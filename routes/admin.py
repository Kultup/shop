from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from flask_wtf.csrf import validate_csrf
from werkzeug.exceptions import BadRequest
from models import db, Product, Order, OrderItem, User, Category, ProductImage, Settings
from forms import ProductForm, OrderStatusForm, CategoryForm, TelegramSettingsForm
from utils import admin_required, save_uploaded_file, delete_file
from sqlalchemy import func
from datetime import datetime, timedelta
from flask_login import current_user
import re

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Головна сторінка адмін-панелі зі статистикою"""
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    processing_orders = Order.query.filter_by(status='processing').count()
    completed_orders = Order.query.filter_by(status='completed').count()
    total_users = User.query.count()
    
    # Статистика замовлень за останні 7 днів
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_orders = Order.query.filter(
        Order.created_at >= seven_days_ago
    ).count()
    
    # Останні замовлення
    latest_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Останні товари
    latest_products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    
    # Топ товарів за кількістю продажів
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    
    # Статистика по статусах
    cancelled_orders = Order.query.filter_by(status='cancelled').count()
    
    # Статистика замовлень за останні 30 днів (для графіку)
    orders_by_day = []
    for i in range(30, -1, -1):
        date = datetime.utcnow() - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = Order.query.filter(
            Order.created_at >= date_start,
            Order.created_at <= date_end
        ).count()
        orders_by_day.append({
            'date': date.strftime('%d.%m'),
            'count': count
        })
    
    # Статистика продажів за останні 7 днів
    sales_by_day = []
    for i in range(6, -1, -1):
        date = datetime.utcnow() - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        total_quantity = db.session.query(
            func.sum(OrderItem.quantity)
        ).join(Order).filter(
            Order.created_at >= date_start,
            Order.created_at <= date_end,
            Order.status != 'cancelled'
        ).scalar() or 0
        sales_by_day.append({
            'date': date.strftime('%d.%m'),
            'quantity': int(total_quantity)
        })
    
    return render_template('admin/dashboard.html',
                         total_products=total_products,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         processing_orders=processing_orders,
                         completed_orders=completed_orders,
                         cancelled_orders=cancelled_orders,
                         total_users=total_users,
                         recent_orders=recent_orders,
                         latest_orders=latest_orders,
                         latest_products=latest_products,
                         top_products=top_products,
                         orders_by_day=orders_by_day,
                         sales_by_day=sales_by_day)


@admin_bp.route('/products')
@login_required
@admin_required
def products():
    """Список товарів"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Product.query
    
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    
    products = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    # Отримуємо всі категорії для масової зміни категорії
    def get_all_categories(categories, result=None):
        if result is None:
            result = []
        for cat in categories:
            result.append(cat)
            if cat.children:
                get_all_categories(cat.children, result)
        return result
    
    main_categories = Category.query.filter_by(parent_id=None).all()
    categories = get_all_categories(main_categories)
    
    return render_template('admin/products.html', products=products, search=search, categories=categories)


@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    """Додати товар"""
    form = ProductForm()
    
    if form.validate_on_submit():
        try:
            # Обробляємо category_id: якщо 0 або None, встановлюємо None
            category_id_value = form.category_id.data
            if category_id_value == 0 or category_id_value is None:
                category_id_value = None
            
            product = Product(
                name=form.name.data,
                description=form.description.data,
                image_url=None,
                category_id=category_id_value,
                is_active=form.is_active.data
            )
            
            db.session.add(product)
            db.session.flush()  # Отримуємо ID товару
            
            # Обробка зображень
            uploaded_images = [img for img in request.files.getlist('image_files') if img and getattr(img, 'filename', '')]
            saved_index = 0
            for img_file in uploaded_images:
                img_path = save_uploaded_file(img_file)
                if img_path:
                    is_primary = saved_index == 0
                    product_image = ProductImage(
                        product_id=product.id,
                        image_url='/' + img_path,
                        is_primary=is_primary,
                        display_order=saved_index
                    )
                    db.session.add(product_image)
                    if is_primary:
                        product.image_url = '/' + img_path
                    saved_index += 1
            
            db.session.commit()
            flash('Товар успішно додано', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Помилка додавання товару: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Помилка додавання товару: {str(e)}', 'error')
    
    return render_template('admin/product_form.html', form=form, title='Додати товар')


@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    """Редагувати товар"""
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    
    # Встановлюємо поточну категорію
    if product.category_id:
        form.category_id.data = product.category_id
    
    if form.validate_on_submit():
        try:
            product.name = form.name.data
            product.description = form.description.data
            # Обробляємо category_id: якщо 0 або None, встановлюємо None
            category_id_value = form.category_id.data
            if category_id_value == 0 or category_id_value is None:
                product.category_id = None
            else:
                product.category_id = category_id_value
            product.is_active = form.is_active.data
            
            # Обробка нових зображень
            uploaded_images = [img for img in request.files.getlist('image_files') if img and getattr(img, 'filename', '')]
            if uploaded_images:
                max_order = db.session.query(db.func.max(ProductImage.display_order)).filter_by(product_id=product.id).scalar()
                if max_order is None:
                    max_order = -1
                saved_index = 0
                for img_file in uploaded_images:
                    img_path = save_uploaded_file(img_file)
                    if img_path:
                        if max_order == -1:
                            display_order = saved_index
                            is_primary = saved_index == 0
                        else:
                            display_order = max_order + 1 + saved_index
                            is_primary = False
                        product_image = ProductImage(
                            product_id=product.id,
                            image_url='/' + img_path,
                            is_primary=is_primary,
                            display_order=display_order
                        )
                        db.session.add(product_image)
                        if is_primary:
                            product.image_url = '/' + img_path
                        saved_index += 1
            
            db.session.commit()
            flash('Товар успішно оновлено', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Помилка збереження товару: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Помилка збереження товару: {str(e)}', 'error')
            # Залишаємося на сторінці редагування
    
    return render_template('admin/product_form.html', form=form, product=product, title='Редагувати товар')


@admin_bp.route('/products/toggle/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def toggle_product_status(product_id):
    """Швидке перемикання статусу активності товару"""
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    
    status_text = "активовано" if product.is_active else "деактивовано"
    flash(f'Товар "{product.name}" успішно {status_text}', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/images/delete/<int:image_id>', methods=['POST'])
@login_required
@admin_required
def delete_product_image(image_id):
    """Видалити зображення товару"""
    try:
        # Перевіряємо CSRF токен
        try:
            validate_csrf(request.form.get('csrf_token'))
        except BadRequest:
            flash('Помилка безпеки. Спробуйте ще раз.', 'error')
            # Спробуємо отримати product_id з referrer або перенаправити назад
            referrer = request.referrer
            if referrer and '/products/edit/' in referrer:
                # Витягуємо product_id з URL
                match = re.search(r'/products/edit/(\d+)', referrer)
                if match:
                    return redirect(url_for('admin.edit_product', product_id=int(match.group(1))))
            return redirect(url_for('admin.products'))
        
        product_image = ProductImage.query.get_or_404(image_id)
        product_id = product_image.product_id
        is_primary = product_image.is_primary
        
        # Перевіряємо що товар існує
        product = Product.query.get(product_id)
        if not product:
            flash('Товар не знайдено', 'error')
            return redirect(url_for('admin.products'))
        
        # Якщо видаляємо головне зображення, спочатку знаходимо нове головне
        if is_primary:
            # Шукаємо інші зображення (крім поточного), сортуємо за порядком
            other_images = ProductImage.query.filter(
                ProductImage.product_id == product_id,
                ProductImage.id != image_id
            ).order_by(ProductImage.display_order.asc()).all()
            
            if other_images:
                # Спочатку знімаємо is_primary з усіх інших (на випадок якщо є помилка в даних)
                for img in other_images:
                    img.is_primary = False
                
                # Робимо перше доступне зображення головним (з найменшим порядком)
                new_primary = other_images[0]
                new_primary.is_primary = True
                # Перенумеровуємо порядок: нове головне стає на позицію 0, решта зміщується
                new_primary_order = new_primary.display_order
                new_primary.display_order = 0
                # Зміщуємо всі зображення, які були перед новим головним
                ProductImage.query.filter(
                    ProductImage.product_id == product_id,
                    ProductImage.id != new_primary.id,
                    ProductImage.display_order < new_primary_order
                ).update({ProductImage.display_order: ProductImage.display_order + 1})
                product.image_url = new_primary.image_url
            else:
                # Якщо немає інших зображень, очищаємо image_url
                product.image_url = None
        
        # Видаляємо файл якщо він локальний
        if product_image.image_url and product_image.image_url.startswith('/static/uploads'):
            try:
                delete_file(product_image.image_url[1:])
            except Exception as e:
                print(f"Помилка видалення файлу: {e}")
        
        # Зберігаємо product_id та порядок перед видаленням
        saved_product_id = int(product_id)
        deleted_order = product_image.display_order
        
        # Видаляємо зображення з бази даних
        db.session.delete(product_image)
        
        # Перенумеровуємо порядок для інших зображень (зменшуємо на 1 для всіх після видаленого)
        ProductImage.query.filter(
            ProductImage.product_id == saved_product_id,
            ProductImage.display_order > deleted_order
        ).update({ProductImage.display_order: ProductImage.display_order - 1})
        
        try:
            db.session.commit()
            flash('Зображення успішно видалено', 'success')
            # Переконуємося, що товар все ще існує перед редиректом
            product_check = Product.query.get(saved_product_id)
            if product_check:
                return redirect(url_for('admin.edit_product', product_id=saved_product_id))
            else:
                flash('Товар не знайдено після видалення зображення', 'error')
                return redirect(url_for('admin.products'))
        except Exception as commit_error:
            db.session.rollback()
            print(f"Помилка commit при видаленні зображення: {commit_error}")
            flash('Помилка збереження змін. Спробуйте ще раз.', 'error')
            return redirect(url_for('admin.edit_product', product_id=saved_product_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Помилка видалення зображення: {e}")
        flash('Помилка видалення зображення. Спробуйте ще раз.', 'error')
        # Спробуємо перенаправити на сторінку редагування товару
        try:
            product_image = ProductImage.query.get(image_id)
            if product_image:
                return redirect(url_for('admin.edit_product', product_id=product_image.product_id))
        except:
            pass
        return redirect(url_for('admin.products'))

@admin_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    """Видалити товар"""
    product = Product.query.get_or_404(product_id)
    
    # Видаляємо головне зображення якщо воно локальне
    if product.image_url and product.image_url.startswith('/static/uploads'):
        delete_file(product.image_url[1:])
    
    # Видаляємо всі додаткові зображення
    for img in product.images:
        if img.image_url and img.image_url.startswith('/static/uploads'):
            delete_file(img.image_url[1:])
    
    db.session.delete(product)
    db.session.commit()
    flash('Товар успішно видалено', 'success')
    return redirect(url_for('admin.products'))


@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    """Список замовлень"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Order.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter)


@admin_bp.route('/orders/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    """Детальна інформація про замовлення"""
    order = Order.query.get_or_404(order_id)
    form = OrderStatusForm()
    form.status.data = order.status  # Встановлюємо поточний статус
    return render_template('admin/order_detail.html', order=order, form=form)


@admin_bp.route('/orders/<int:order_id>/print')
@login_required
@admin_required
def print_order(order_id):
    """Друк замовлення"""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_print.html', order=order)


@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    """Оновити статус замовлення"""
    order = Order.query.get_or_404(order_id)
    form = OrderStatusForm()
    
    if form.validate_on_submit():
        order.status = form.status.data
        order.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Статус замовлення оновлено', 'success')
        return redirect(url_for('admin.order_detail', order_id=order_id))
    
    flash('Помилка оновлення статусу', 'error')
    return redirect(url_for('admin.order_detail', order_id=order_id))


# Маршрути для категорій
@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """Список категорій"""
    categories_list = Category.query.order_by(Category.parent_id, Category.name).all()
    return render_template('admin/categories.html', categories=categories_list)


@admin_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    """Додати категорію"""
    form = CategoryForm()
    
    if form.validate_on_submit():
        # Явно перевіряємо, чи вибрано батьківську категорію (0 означає "Без батьківської категорії")
        parent_id = None
        parent_id_value = form.parent_id.data
        
        # Додаткова перевірка: якщо значення не встановлено або дорівнює 0, то parent_id = None
        if parent_id_value is not None and parent_id_value != 0:
            # Перевіряємо, чи категорія з таким ID існує
            parent_category = Category.query.get(parent_id_value)
            if parent_category:
                parent_id = parent_id_value
            else:
                # Якщо категорія не знайдена, встановлюємо None
                parent_id = None
        
        category = Category(
            name=form.name.data,
            parent_id=parent_id
        )
        db.session.add(category)
        db.session.commit()
        flash('Категорію успішно додано', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/category_form.html', form=form, title='Додати категорію')


@admin_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    """Редагувати категорію"""
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    
    # Встановлюємо parent_id в формі: якщо є батьківська категорія - встановлюємо її ID, якщо ні - встановлюємо 0
    if category.parent_id:
        form.parent_id.data = category.parent_id
    else:
        form.parent_id.data = 0  # "Без батьківської категорії"
    
    if form.validate_on_submit():
        category.name = form.name.data
        # Явно перевіряємо, чи вибрано батьківську категорію (0 означає "Без батьківської категорії")
        parent_id_value = form.parent_id.data
        category.parent_id = None
        
        # Додаткова перевірка: якщо значення не встановлено або дорівнює 0, то parent_id = None
        if parent_id_value is not None and parent_id_value != 0:
            # Перевіряємо, чи категорія з таким ID існує
            parent_category = Category.query.get(parent_id_value)
            if parent_category:
                category.parent_id = parent_id_value
            else:
                # Якщо категорія не знайдена, встановлюємо None
                category.parent_id = None
        
        db.session.commit()
        flash('Категорію успішно оновлено', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/category_form.html', form=form, category=category, title='Редагувати категорію')


@admin_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """Видалити категорію"""
    category = Category.query.get_or_404(category_id)
    
    # Перевіряємо чи немає товарів або підкатегорій
    if category.products:
        flash('Неможливо видалити категорію, в якій є товари', 'error')
        return redirect(url_for('admin.categories'))
    
    if category.children:
        flash('Неможливо видалити категорію, яка має підкатегорії', 'error')
        return redirect(url_for('admin.categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Категорію успішно видалено', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/products/bulk/activate', methods=['POST'])
@login_required
@admin_required
def bulk_activate_products():
    """Масове активування товарів"""
    product_ids = request.form.get('product_ids', '').split(',')
    product_ids = [int(id) for id in product_ids if id.strip().isdigit()]
    
    if product_ids:
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        for product in products:
            product.is_active = True
        db.session.commit()
        flash(f'Успішно активовано {len(products)} товар(ів)', 'success')
    else:
        flash('Не вибрано товарів для активації', 'error')
    
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/bulk/deactivate', methods=['POST'])
@login_required
@admin_required
def bulk_deactivate_products():
    """Масове деактивування товарів"""
    product_ids = request.form.get('product_ids', '').split(',')
    product_ids = [int(id) for id in product_ids if id.strip().isdigit()]
    
    if product_ids:
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        for product in products:
            product.is_active = False
        db.session.commit()
        flash(f'Успішно деактивовано {len(products)} товар(ів)', 'success')
    else:
        flash('Не вибрано товарів для деактивації', 'error')
    
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/bulk/delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete_products():
    """Масове видалення товарів"""
    product_ids = request.form.get('product_ids', '').split(',')
    product_ids = [int(id) for id in product_ids if id.strip().isdigit()]
    
    if product_ids:
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        deleted_count = 0
        for product in products:
            # Видаляємо головне зображення
            if product.image_url and product.image_url.startswith('/static/uploads'):
                delete_file(product.image_url[1:])
            
            # Видаляємо всі додаткові зображення
            for img in product.images:
                if img.image_url and img.image_url.startswith('/static/uploads'):
                    delete_file(img.image_url[1:])
            
            db.session.delete(product)
            deleted_count += 1
        
        db.session.commit()
        flash(f'Успішно видалено {deleted_count} товар(ів)', 'success')
    else:
        flash('Не вибрано товарів для видалення', 'error')
    
    return redirect(url_for('admin.products'))


@admin_bp.route('/products/bulk/change-category', methods=['POST'])
@login_required
@admin_required
def bulk_change_category():
    """Масове зміна категорії товарів"""
    product_ids = request.form.get('product_ids', '').split(',')
    product_ids = [int(id) for id in product_ids if id.strip().isdigit()]
    category_id = request.form.get('category_id', type=int)
    
    if product_ids and category_id:
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        for product in products:
            product.category_id = category_id
        db.session.commit()
        flash(f'Успішно змінено категорію для {len(products)} товар(ів)', 'success')
    elif not category_id:
        flash('Не вибрано категорію', 'error')
    else:
        flash('Не вибрано товарів', 'error')
    
    return redirect(url_for('admin.products'))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Список користувачів"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    
    if search:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                User.username.contains(search),
                User.email.contains(search),
                User.city.contains(search),
                User.institution.contains(search)
            )
        )
    
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/users.html', users=users, search=search)


@admin_bp.route('/users/<int:user_id>/toggle-block', methods=['POST'])
@login_required
@admin_required
def toggle_user_block(user_id):
    """Блокування/розблокування користувача"""
    user = User.query.get_or_404(user_id)
    
    # Не можна блокувати себе
    if user.id == current_user.id:
        flash('Ви не можете заблокувати самого себе', 'error')
        return redirect(url_for('admin.users'))
    
    # Не можна блокувати інших адмінів
    if user.is_admin:
        flash('Не можна блокувати адміністраторів', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_blocked = not user.is_blocked
    db.session.commit()
    
    status = 'заблоковано' if user.is_blocked else 'розблоковано'
    flash(f'Користувач {user.username} успішно {status}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/orders')
@login_required
@admin_required
def user_orders(user_id):
    """Замовлення користувача"""
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    
    # Статистика
    total_orders = len(orders)
    pending_count = sum(1 for o in orders if o.status == 'pending')
    processing_count = sum(1 for o in orders if o.status == 'processing')
    completed_count = sum(1 for o in orders if o.status == 'completed')
    cancelled_count = sum(1 for o in orders if o.status == 'cancelled')
    
    return render_template('admin/user_orders.html', 
                         user=user, 
                         orders=orders,
                         total_orders=total_orders,
                         pending_count=pending_count,
                         processing_count=processing_count,
                         completed_count=completed_count,
                         cancelled_count=cancelled_count)


@admin_bp.route('/settings/telegram', methods=['GET', 'POST'])
@login_required
@admin_required
def telegram_settings():
    """Налаштування Telegram бота"""
    form = TelegramSettingsForm()
    
    # Завантажуємо поточні налаштування
    if request.method == 'GET':
        form.bot_token.data = Settings.get_setting('telegram_bot_token', '')
        form.chat_id.data = Settings.get_setting('telegram_chat_id', '')
        form.enabled.data = Settings.get_setting('telegram_enabled', 'false').lower() == 'true'
    
    if form.validate_on_submit():
        # Зберігаємо налаштування
        Settings.set_setting('telegram_bot_token', form.bot_token.data or '')
        Settings.set_setting('telegram_chat_id', form.chat_id.data or '')
        Settings.set_setting('telegram_enabled', 'true' if form.enabled.data else 'false')
        
        flash('Налаштування Telegram успішно збережено!', 'success')
        return redirect(url_for('admin.telegram_settings'))
    
    return render_template('admin/telegram_settings.html', form=form)

