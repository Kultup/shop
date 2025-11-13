from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from models import User, Product, Category

class LoginForm(FlaskForm):
    """Форма входу"""
    username = StringField('Ім\'я користувача', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Увійти')


class RegisterForm(FlaskForm):
    """Форма реєстрації"""
    username = StringField('Логін', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Пошта', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Підтвердження паролю', validators=[DataRequired(), EqualTo('password', message='Паролі не співпадають')])
    city = StringField('Місто', validators=[DataRequired(), Length(max=100)])
    institution = StringField('Заклад', validators=[DataRequired(), Length(max=200)])
    submit = SubmitField('Зареєструватися')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Це ім\'я користувача вже зайняте.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Цей email вже зареєстрований.')


class CategoryForm(FlaskForm):
    """Форма для категорії"""
    name = StringField('Назва категорії', validators=[DataRequired(), Length(max=100)])
    parent_id = SelectField('Батьківська категорія', coerce=int, validators=[Optional()])
    submit = SubmitField('Зберегти')
    
    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.parent_id.choices = [(0, 'Без батьківської категорії')]
        categories = Category.query.filter_by(parent_id=None).all()
        for cat in categories:
            self.parent_id.choices.append((cat.id, cat.name))
        # Явно встановлюємо значення за замовчуванням на 0 (Без батьківської категорії)
        # якщо значення не було встановлено через obj=category
        if self.parent_id.data is None:
            self.parent_id.data = 0


class ProductForm(FlaskForm):
    """Форма для товару"""
    name = StringField('Назва', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Опис')
    image_files = MultipleFileField('Фото товару (можна вибрати кілька, перше стане головним)', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Тільки зображення!')])
    category_id = SelectField('Категорія', coerce=int, validators=[Optional()])
    is_active = BooleanField('Товар активний (відображається на сайті)', default=True)
    submit = SubmitField('Зберегти')
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(0, 'Без категорії')]
        # Додаємо всі категорії з повним шляхом
        def add_categories(categories, prefix=""):
            for cat in categories:
                full_name = f"{prefix}{cat.name}"
                self.category_id.choices.append((cat.id, full_name))
                if cat.children:
                    add_categories(cat.children, f"{full_name} > ")
        
        main_categories = Category.query.filter_by(parent_id=None).all()
        add_categories(main_categories)


class OrderStatusForm(FlaskForm):
    """Форма для зміни статусу замовлення"""
    status = SelectField('Статус', choices=[
        ('pending', 'Очікує'),
        ('processing', 'Обробляється'),
        ('completed', 'Завершено'),
        ('cancelled', 'Скасовано')
    ], validators=[DataRequired()])
    submit = SubmitField('Оновити статус')


class EditProfileForm(FlaskForm):
    """Форма редагування профілю"""
    username = StringField('Логін', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Пошта', validators=[DataRequired(), Email()])
    city = StringField('Місто', validators=[DataRequired(), Length(max=100)])
    institution = StringField('Заклад', validators=[DataRequired(), Length(max=200)])
    submit = SubmitField('Зберегти зміни')
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Це ім\'я користувача вже зайняте.')
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Цей email вже зареєстрований.')


class ChangePasswordForm(FlaskForm):
    """Форма зміни паролю"""
    current_password = PasswordField('Поточний пароль', validators=[DataRequired()])
    new_password = PasswordField('Новий пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Підтвердження нового паролю', validators=[DataRequired(), EqualTo('new_password', message='Паролі не співпадають')])
    submit = SubmitField('Змінити пароль')


class TelegramSettingsForm(FlaskForm):
    """Форма налаштувань Telegram бота"""
    bot_token = StringField('Токен бота', validators=[Optional(), Length(max=200)], 
                           description='Токен бота отриманий від @BotFather')
    chat_id = StringField('Chat ID групи', validators=[Optional(), Length(max=100)],
                         description='ID групи або каналу (можна отримати через @getidsbot)')
    enabled = BooleanField('Увімкнути Telegram повідомлення', default=False)
    submit = SubmitField('Зберегти налаштування')

