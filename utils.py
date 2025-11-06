from functools import wraps
from flask import abort
from flask_login import current_user
import os
from werkzeug.utils import secure_filename
from config import Config

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def admin_required(f):
    """Декоратор для перевірки прав адміністратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Перевірка чи файл має дозволене розширення"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file, folder='products'):
    """Збереження завантаженого файлу"""
    if file and allowed_file(file.filename):
        # Створюємо директорію якщо її немає
        upload_path = os.path.join(Config.UPLOAD_FOLDER, folder)
        os.makedirs(upload_path, exist_ok=True)
        
        # Безпечне ім'я файлу
        filename = secure_filename(file.filename)
        
        # Додаємо timestamp для унікальності
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        filepath = os.path.join(upload_path, filename)
        
        # Зберігаємо файл
        file.save(filepath)
        
        # Оптимізуємо зображення
        if HAS_PIL:
            try:
                img = Image.open(filepath)
                # Конвертуємо в RGB якщо потрібно
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                # Зберігаємо з оптимізацією
                img.save(filepath, optimize=True, quality=85)
            except Exception as e:
                print(f"Помилка оптимізації зображення: {e}")
        
        # Повертаємо відносний шлях
        return os.path.join(Config.UPLOAD_FOLDER, folder, filename).replace('\\', '/')
    return None

def delete_file(filepath):
    """Видалення файлу"""
    if filepath and filepath.startswith(Config.UPLOAD_FOLDER):
        full_path = os.path.join(os.getcwd(), filepath)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                return True
            except Exception as e:
                print(f"Помилка видалення файлу: {e}")
    return False

def send_telegram_message(message):
    """Відправка повідомлення в Telegram групу"""
    try:
        from models import Settings
        
        # Спочатку перевіряємо налаштування з бази даних
        enabled = Settings.get_setting('telegram_enabled', 'false').lower() == 'true'
        bot_token = Settings.get_setting('telegram_bot_token', '')
        chat_id = Settings.get_setting('telegram_chat_id', '')
        
        # Якщо в БД немає налаштувань, використовуємо config
        if not bot_token:
            bot_token = Config.TELEGRAM_BOT_TOKEN
        if not chat_id:
            chat_id = Config.TELEGRAM_CHAT_ID
        if not enabled:
            enabled = Config.TELEGRAM_ENABLED
        
        if not enabled or not bot_token or not chat_id:
            return False
        
        import requests
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except ImportError:
        print("Помилка: бібліотека requests не встановлена")
        return False
    except Exception as e:
        print(f"Помилка відправки повідомлення в Telegram: {e}")
        return False
