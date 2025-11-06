from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import LoginForm, RegisterForm, EditProfileForm, ChangePasswordForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Сторінка входу"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            # Перевірка чи користувач не заблокований
            if user.is_blocked:
                flash('Ваш акаунт заблоковано. Зверніться до адміністратора.', 'error')
                return render_template('login.html', form=form)
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        flash('Невірне ім\'я користувача або пароль', 'error')
    
    return render_template('login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Сторінка реєстрації"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            city=form.city.data,
            institution=form.institution.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Реєстрація успішна! Тепер ви можете увійти.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Вихід"""
    logout_user()
    flash('Ви вийшли з системи', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Сторінка профілю користувача"""
    edit_form = EditProfileForm(
        original_username=current_user.username,
        original_email=current_user.email,
        obj=current_user
    )
    password_form = ChangePasswordForm()
    
    # Обробка форми редагування профілю
    if edit_form.validate_on_submit() and 'edit_profile' in request.form:
        current_user.username = edit_form.username.data
        current_user.email = edit_form.email.data
        current_user.city = edit_form.city.data
        current_user.institution = edit_form.institution.data
        db.session.commit()
        flash('Профіль успішно оновлено!', 'success')
        return redirect(url_for('auth.profile'))
    
    # Обробка форми зміни паролю
    if password_form.validate_on_submit() and 'change_password' in request.form:
        if not current_user.check_password(password_form.current_password.data):
            flash('Невірний поточний пароль', 'error')
            return redirect(url_for('auth.profile'))
        
        current_user.set_password(password_form.new_password.data)
        db.session.commit()
        flash('Пароль успішно змінено!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('profile.html', edit_form=edit_form, password_form=password_form)

