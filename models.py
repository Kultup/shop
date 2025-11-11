from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Category(db.Model):
    """Модель категорії"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Зв'язки
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy=True)
    products = db.relationship('Product', backref='category_obj', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    @property
    def full_path(self):
        """Повний шлях категорії (батьківська категорія > категорія)"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class User(UserMixin, db.Model):
    """Модель користувача"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100))
    institution = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Зв'язки
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True)
    
    def set_password(self, password):
        """Встановити пароль"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Перевірити пароль"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Product(db.Model):
    """Модель товару"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))  # Головне зображення (для зворотної сумісності)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Чи активний товар
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Для зворотної сумісності (старе поле category)
    category = db.Column(db.String(100))
    
    # Зв'язки
    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade='all, delete-orphan', order_by='ProductImage.created_at')
    
    def __repr__(self):
        return f'<Product {self.name}>'
    
    @property
    def main_image(self):
        """Повертає головне зображення (з is_primary=True або перше з images або image_url)"""
        # Шукаємо зображення з is_primary=True
        primary_image = next((img for img in self.images if img.is_primary), None)
        if primary_image:
            return primary_image.image_url
        # Якщо немає головного, беремо перше додаткове
        if self.images:
            return self.images[0].image_url
        # Для зворотної сумісності використовуємо image_url
        return self.image_url
    
    @property
    def additional_images(self):
        """Повертає додаткові зображення (без головного)"""
        return [img for img in self.images if not img.is_primary]


class ProductImage(db.Model):
    """Модель зображення товару"""
    __tablename__ = 'product_images'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)  # Чи є головним зображенням
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProductImage {self.id}>'


class CartItem(db.Model):
    """Модель елемента кошика"""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CartItem {self.id}>'


class Order(db.Model):
    """Модель замовлення"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)  # pending, processing, completed, cancelled
    city = db.Column(db.String(100))
    institution = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Зв'язки
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    """Модель елемента замовлення"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'


class Settings(db.Model):
    """Модель налаштувань системи"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Settings {self.key}={self.value}>'
    
    @staticmethod
    def get_setting(key, default=None):
        """Отримати налаштування за ключем"""
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set_setting(key, value):
        """Встановити налаштування"""
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Settings(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting

