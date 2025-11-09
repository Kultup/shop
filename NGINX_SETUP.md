# 🔧 Налаштування Nginx для проекту "Країна Мрій"

Цей документ описує кроки для налаштування Nginx як reverse proxy для Flask додатку.

## 📋 Передумови

- Встановлений Nginx
- Встановлений Gunicorn
- Flask додаток налаштований та працює
- Домен налаштований (опціонально, для SSL)

## 🚀 Крок 1: Встановлення Gunicorn

```bash
# Активація віртуального середовища
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows

# Встановлення Gunicorn
pip install gunicorn
```

## 🚀 Крок 2: Налаштування Gunicorn

1. Відредагуйте `gunicorn_config.py`:
   - Змініть шляхи на реальні
   - Налаштуйте кількість воркерів
   - Налаштуйте логування

2. Створіть папку для логів:
```bash
mkdir -p logs
```

3. Протестуйте запуск Gunicorn:
```bash
gunicorn -c gunicorn_config.py app:app
```

## 🚀 Крок 3: Налаштування Nginx

1. Відредагуйте `nginx.conf`:
   - Замініть `/path/to/shop` на реальний шлях до проекту
   - Замініть `example.com` на ваш домен
   - Налаштуйте SSL сертифікати (якщо використовуєте HTTPS)

2. Скопіюйте конфігурацію:
```bash
sudo cp nginx.conf /etc/nginx/sites-available/shop
```

3. Створіть символічне посилання:
```bash
sudo ln -s /etc/nginx/sites-available/shop /etc/nginx/sites-enabled/
```

4. Видаліть конфігурацію за замовчуванням (якщо потрібно):
```bash
sudo rm /etc/nginx/sites-enabled/default
```

5. Перевірте конфігурацію:
```bash
sudo nginx -t
```

6. Перезавантажте Nginx:
```bash
sudo systemctl reload nginx
```

## 🔒 Крок 4: Налаштування SSL (Let's Encrypt)

1. Встановіть Certbot:
```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

2. Отримайте сертифікат:
```bash
sudo certbot --nginx -d example.com -d www.example.com
```

3. Автоматичне оновлення:
```bash
sudo certbot renew --dry-run
```

## 🔧 Крок 5: Налаштування Systemd Service

1. Відредагуйте `shop.service`:
   - Замініть `/path/to/shop` на реальний шлях
   - Налаштуйте користувача та групу
   - Додайте змінні оточення

2. Скопіюйте service файл:
```bash
sudo cp shop.service /etc/systemd/system/
```

3. Перезавантажте systemd:
```bash
sudo systemctl daemon-reload
```

4. Увімкніть автозапуск:
```bash
sudo systemctl enable shop
```

5. Запустіть сервіс:
```bash
sudo systemctl start shop
```

6. Перевірте статус:
```bash
sudo systemctl status shop
```

## 📊 Перевірка роботи

1. Перевірте логи Gunicorn:
```bash
tail -f logs/gunicorn_access.log
tail -f logs/gunicorn_error.log
```

2. Перевірте логи Nginx:
```bash
sudo tail -f /var/log/nginx/shop_access.log
sudo tail -f /var/log/nginx/shop_error.log
```

3. Перевірте статус сервісів:
```bash
sudo systemctl status shop
sudo systemctl status nginx
```

## 🔍 Налагодження

### Проблема: 502 Bad Gateway

**Причини:**
- Gunicorn не запущений
- Неправильний порт в nginx.conf
- Проблеми з правами доступу

**Рішення:**
```bash
# Перевірте чи працює Gunicorn
sudo systemctl status shop

# Перевірте порт
sudo netstat -tlnp | grep 8000

# Перевірте логи
sudo journalctl -u shop -f
```

### Проблема: Статичні файли не завантажуються

**Причини:**
- Неправильний шлях в nginx.conf
- Проблеми з правами доступу

**Рішення:**
```bash
# Перевірте права доступу
ls -la /path/to/shop/static/

# Перевірте конфігурацію nginx
sudo nginx -t
```

### Проблема: SSL сертифікат не працює

**Рішення:**
```bash
# Перевірте сертифікат
sudo certbot certificates

# Оновіть сертифікат
sudo certbot renew
```

## 🔐 Безпека

1. **Оновіть SECRET_KEY** в `shop.service` та `config.py`
2. **Налаштуйте firewall**:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
3. **Регулярно оновлюйте залежності**:
```bash
pip list --outdated
pip install --upgrade package_name
```

## 📝 Корисні команди

```bash
# Перезапуск Gunicorn
sudo systemctl restart shop

# Перезавантаження Nginx
sudo systemctl reload nginx

# Перегляд логів Gunicorn
sudo journalctl -u shop -f

# Перегляд логів Nginx
sudo tail -f /var/log/nginx/shop_error.log

# Перевірка конфігурації Nginx
sudo nginx -t

# Перевірка портів
sudo netstat -tlnp | grep -E '8000|443|80'
```

## 🎯 Оптимізація продуктивності

1. **Кешування статичних файлів** - вже налаштовано в nginx.conf
2. **Gzip стиснення** - додайте в nginx.conf:
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
```
3. **Кешування в браузері** - вже налаштовано для статичних файлів

## 📚 Додаткові ресурси

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

