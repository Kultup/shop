import multiprocessing
import os

# Шлях до проекту
basedir = os.path.abspath(os.path.dirname(__file__))

# WSGI додаток
wsgi_app = "app:app"

# Адреса та порт
bind = "127.0.0.1:8000"

# Кількість воркерів (рекомендовано: 2 * CPU cores + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# Тип воркерів
worker_class = "sync"

# Таймаути
timeout = 60
keepalive = 5

# Логування
accesslog = os.path.join(basedir, "logs", "gunicorn_access.log")
errorlog = os.path.join(basedir, "logs", "gunicorn_error.log")
loglevel = "info"

# Формат логів
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Перезапуск воркерів після N запитів (для запобігання витокам пам'яті)
max_requests = 1000
max_requests_jitter = 50

# Перезапуск воркерів через певний час (години)
worker_tmp_dir = "/dev/shm"  # Використовує RAM для тимчасових файлів (швидше)

# Ім'я процесу
proc_name = "shop"

# User та Group (замініть на ваші)
# user = "www-data"
# group = "www-data"

# PID файл
pidfile = os.path.join(basedir, "gunicorn.pid")

# Daemon mode (запуск у фоні)
daemon = False

# Перезавантаження при зміні коду (тільки для розробки!)
reload = False

# Environment variables
raw_env = [
    'FLASK_ENV=production',
]

