from flask import Flask, render_template
from flask_login import LoginManager, current_user
from flask_wtf.csrf import generate_csrf
from config import Config
from models import db, User, CartItem
from routes.auth import auth_bp
from routes.main import main_bp
from routes.admin import admin_bp

def create_app():
    """Створення та налаштування Flask додатку"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Ініціалізація розширень
    db.init_app(app)
    
    # Налаштування Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Будь ласка, увійдіть для доступу до цієї сторінки.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Контекстний процесор для кількості товарів у кошику та CSRF токена
    @app.context_processor
    def inject_globals():
        cart_count = 0
        try:
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
                cart_count = sum(item.quantity for item in cart_items)
        except:
            pass
        
        def csrf_token():
            """Генерує CSRF токен для використання в шаблонах"""
            return generate_csrf()
        
        return dict(cart_count=cart_count, csrf_token=csrf_token)
    
    # Обробка помилок
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    # Реєстрація Blueprint
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    
    # Створення таблиць бази даних
    with app.app_context():
        db.create_all()
        
        # Міграція: додавання колонки is_active до таблиці products (якщо не існує)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Перевіряємо чи існує таблиця products
            if 'products' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('products')]
                if 'is_active' not in columns:
                    print("Додаємо колонку is_active до таблиці products...")
                    with db.engine.begin() as conn:
                        # SQLite не підтримує BOOLEAN, використовуємо INTEGER (0 = False, 1 = True)
                        conn.execute(text("ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1 NOT NULL"))
                    print("Колонка is_active успішно додана!")
        except Exception as e:
            print(f"Помилка при міграції is_active (можливо колонка вже існує): {e}")
        
        # Міграція: створення таблиці product_images (якщо не існує)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            if 'product_images' not in tables:
                print("Створюємо таблицю product_images...")
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE product_images (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            product_id INTEGER NOT NULL,
                            image_url VARCHAR(500) NOT NULL,
                            is_primary INTEGER DEFAULT 0 NOT NULL,
                            display_order INTEGER DEFAULT 0 NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                        )
                    """))
                print("Таблиця product_images успішно створена!")
            else:
                # Міграція: додавання колонки display_order до таблиці product_images (якщо не існує)
                columns = [col['name'] for col in inspector.get_columns('product_images')]
                if 'display_order' not in columns:
                    print("Додаємо колонку display_order до таблиці product_images...")
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE product_images ADD COLUMN display_order INTEGER DEFAULT 0 NOT NULL"))
                        # Встановлюємо порядок для існуючих зображень
                        conn.execute(text("""
                            UPDATE product_images 
                            SET display_order = (
                                SELECT COUNT(*) 
                                FROM product_images p2 
                                WHERE p2.product_id = product_images.product_id 
                                AND (p2.created_at < product_images.created_at OR (p2.created_at = product_images.created_at AND p2.id <= product_images.id))
                            ) - 1
                        """))
                    print("Колонка display_order успішно додана!")
        except Exception as e:
            print(f"Помилка при міграції product_images (можливо таблиця вже існує): {e}")
        
        # Міграція: створення таблиці settings (якщо не існує)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            if 'settings' not in tables:
                print("Створюємо таблицю settings...")
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE settings (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            key VARCHAR(100) NOT NULL UNIQUE,
                            value TEXT,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                print("Таблиця settings успішно створена!")
        except Exception as e:
            print(f"Помилка при міграції settings (можливо таблиця вже існує): {e}")
        
        # Міграція: додавання колонки is_blocked до таблиці users (якщо не існує)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('users')]
                if 'is_blocked' not in columns:
                    print("Додаємо колонку is_blocked до таблиці users...")
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0 NOT NULL"))
                    print("Колонка is_blocked успішно додана!")
        except Exception as e:
            print(f"Помилка при міграції is_blocked (можливо колонка вже існує): {e}")
        
        # Створюємо директорію для завантажених файлів
        import os
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), Config.UPLOAD_FOLDER)
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(os.path.join(upload_dir, 'products'), exist_ok=True)
        
        # Створення адміністратора за замовчуванням (якщо його немає)
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Створено адміністратора: username='admin', password='admin123'")
    
    return app

# Створюємо глобальну змінну app для Gunicorn
# Gunicorn очікує змінну app на рівні модуля, а не всередині if __name__ == '__main__'
app = create_app()

if __name__ == '__main__':
    # Для локального запуску (python3 app.py або python app.py)
    app.run(debug=True, host='0.0.0.0', port=5000)

