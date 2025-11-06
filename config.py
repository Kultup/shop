import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///shop.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Налаштування для завантаження файлів
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB максимум
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Налаштування Telegram бота
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or ''  # Токен бота
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID') or ''  # ID групи або каналу
    TELEGRAM_ENABLED = os.environ.get('TELEGRAM_ENABLED', 'false').lower() == 'true'  # Увімкнути/вимкнути
