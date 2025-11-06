from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user, logout_user
from models import db, Product, CartItem, Order, OrderItem, Category
from sqlalchemy import func
from datetime import datetime
from utils import send_telegram_message
from functools import wraps

main_bp = Blueprint('main', __name__)

def check_user_blocked(f):
    """Декоратор для перевірки чи користувач не заблокований"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.is_blocked:
            flash('Ваш акаунт заблоковано. Зверніться до адміністратора.', 'error')
            logout_user()
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def index():
    """Головна сторінка з каталогом товарів"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'newest')  # newest, name_asc, name_desc
    
    # Показуємо всі товари (активні та неактивні), неактивні будуть тусклі
    query = Product.query
    
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    # Сортування
    # Спочатку активні товари, потім неактивні
    if sort_by == 'name_asc':
        query = query.order_by(Product.is_active.desc(), Product.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Product.is_active.desc(), Product.name.desc())
    else:  # newest (за замовчуванням)
        query = query.order_by(Product.is_active.desc(), Product.created_at.desc())
    
    products = query.paginate(page=page, per_page=25, error_out=False)
    
    # Отримуємо список категорій з підкатегоріями
    def get_categories_tree():
        main_categories = Category.query.filter_by(parent_id=None).all()
        result = []
        for cat in main_categories:
            result.append({
                'id': cat.id,
                'name': cat.name,
                'full_path': cat.name,
                'children': [{'id': child.id, 'name': child.name, 'full_path': child.full_path} 
                            for child in cat.children]
            })
        return result
    
    categories = get_categories_tree()
    
    return render_template('index.html', products=products, categories=categories, 
                         current_category_id=category_id, search=search, sort_by=sort_by)


@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """Детальна сторінка товару"""
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)


@main_bp.route('/cart')
@check_user_blocked
def cart():
    """Сторінка кошика"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', cart_items=cart_items)


@main_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@check_user_blocked
def add_to_cart(product_id):
    """Додати товар до кошика"""
    product = Product.query.get_or_404(product_id)
    quantity = request.form.get('quantity', 1, type=int)
    
    if quantity <= 0:
        flash('Кількість повинна бути більше 0', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
    
    # Перевіряємо чи товар вже в кошику
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Товар додано до кошика', 'success')
    return redirect(url_for('main.cart'))


@main_bp.route('/cart/update/<int:cart_item_id>', methods=['POST'])
@check_user_blocked
def update_cart_item(cart_item_id):
    """Оновити кількість товару в кошику"""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    
    if cart_item.user_id != current_user.id:
        flash('Немає доступу', 'error')
        return redirect(url_for('main.cart'))
    
    quantity = request.form.get('quantity', 1, type=int)
    
    if quantity <= 0:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Товар видалено з кошика', 'info')
        return redirect(url_for('main.cart'))
    
    cart_item.quantity = quantity
    db.session.commit()
    flash('Кошик оновлено', 'success')
    return redirect(url_for('main.cart'))


@main_bp.route('/cart/remove/<int:cart_item_id>', methods=['POST'])
@check_user_blocked
def remove_from_cart(cart_item_id):
    """Видалити товар з кошика"""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    
    if cart_item.user_id != current_user.id:
        flash('Немає доступу', 'error')
        return redirect(url_for('main.cart'))
    
    db.session.delete(cart_item)
    db.session.commit()
    flash('Товар видалено з кошика', 'info')
    return redirect(url_for('main.cart', deleted=1))


@main_bp.route('/cart/checkout', methods=['POST'])
@check_user_blocked
def checkout():
    """Оформити замовлення"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Кошик порожній', 'error')
        return redirect(url_for('main.cart'))
    
    # Створюємо замовлення з автоматичним заповненням даних користувача
    order = Order(
        user_id=current_user.id,
        status='pending',
        city=current_user.city,
        institution=current_user.institution
    )
    db.session.add(order)
    db.session.flush()  # Отримуємо ID замовлення
    
    # Створюємо елементи замовлення
    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.session.add(order_item)
        
        # Видаляємо з кошика
        db.session.delete(item)
    
    db.session.commit()
    
    # Відправляємо повідомлення в Telegram
    try:
        # Формуємо повідомлення про нове замовлення
        message = f"🛒 <b>Нове замовлення #{order.id}</b>\n\n"
        message += f"👤 <b>Користувач:</b> {current_user.username}\n"
        message += f"📧 <b>Email:</b> {current_user.email}\n"
        message += f"🏙️ <b>Місто:</b> {current_user.city or 'Не вказано'}\n"
        message += f"🏢 <b>Заклад:</b> {current_user.institution or 'Не вказано'}\n\n"
        message += f"📦 <b>Товари:</b>\n"
        
        total_items = 0
        for item in order.items:
            product = item.product
            category_path = product.category_obj.full_path if product.category_obj else (product.category or 'Без категорії')
            message += f"  • {product.name} ({category_path}) - {item.quantity} шт.\n"
            total_items += item.quantity
        
        message += f"\n📊 <b>Всього товарів:</b> {total_items} шт.\n"
        message += f"📅 <b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        
        # Отримуємо URL для адмін-панелі
        from flask import url_for
        try:
            admin_url = url_for('admin.order_detail', order_id=order.id, _external=True)
            message += f"\n🔗 <a href='{admin_url}'>Переглянути замовлення</a>"
        except:
            # Якщо не вдається отримати URL, просто вказуємо ID
            message += f"\n🔗 ID замовлення: {order.id}"
        
        send_telegram_message(message)
    except Exception as e:
        print(f"Помилка відправки повідомлення в Telegram: {e}")
        # Не перериваємо процес оформлення замовлення через помилку Telegram
    
    flash('Замовлення успішно оформлено!', 'success')
    return redirect(url_for('main.orders'))


@main_bp.route('/orders')
@check_user_blocked
def orders():
    """Історія замовлень користувача"""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)


@main_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@check_user_blocked
def cancel_order(order_id):
    """Скасувати замовлення (тільки для pending)"""
    order = Order.query.get_or_404(order_id)
    
    # Перевіряємо що замовлення належить користувачу
    if order.user_id != current_user.id:
        flash('Немає доступу', 'error')
        return redirect(url_for('main.orders'))
    
    # Перевіряємо що замовлення має статус pending
    if order.status != 'pending':
        flash('Можна скасувати тільки замовлення зі статусом "Очікує обробки"', 'error')
        return redirect(url_for('main.orders'))
    
    # Змінюємо статус на cancelled
    order.status = 'cancelled'
    db.session.commit()
    
    flash('Замовлення успішно скасовано', 'success')
    return redirect(url_for('main.orders'))


@main_bp.route('/api/cart/sync', methods=['POST'])
@check_user_blocked
def sync_cart():
    """Синхронізація кошика з localStorage"""
    try:
        data = request.get_json()
        cart_items = data.get('cart', [])
        
        synced = 0
        for item in cart_items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            
            if not product_id or quantity <= 0:
                continue
            
            # Перевіряємо чи товар існує та активний
            product = Product.query.get(product_id)
            if not product or not product.is_active:
                continue
            
            # Перевіряємо чи товар вже в кошику
            cart_item = CartItem.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()
            
            if cart_item:
                # Оновлюємо кількість (беремо максимум)
                cart_item.quantity = max(cart_item.quantity, quantity)
            else:
                # Додаємо новий товар
                cart_item = CartItem(
                    user_id=current_user.id,
                    product_id=product_id,
                    quantity=quantity
                )
                db.session.add(cart_item)
                synced += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'synced': synced,
            'message': f'Синхронізовано {synced} товарів'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Помилка синхронізації: {str(e)}'
        }), 400


@main_bp.route('/api/cart', methods=['GET'])
@check_user_blocked
def get_cart():
    """Отримати поточний стан кошика"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    cart_data = [{
        'product_id': item.product_id,
        'quantity': item.quantity
    } for item in cart_items]
    return jsonify({'cart': cart_data})

