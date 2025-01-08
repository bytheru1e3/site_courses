from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db
import logging

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Если пользователь уже вошел в систему, отправляем его на главную страницу
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        # Проверяем, что все поля заполнены
        if not all([username, email, password, password_confirm]):
            flash('Пожалуйста, заполните все поля', 'error')
            return render_template('auth/register.html')

        # Проверяем существование пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('auth/register.html')

        # Проверяем совпадение паролей
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('auth/register.html')

        # Регистрируем нового пользователя
        try:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"Пользователь {username} успешно зарегистрирован")
            flash('Регистрация успешна! Теперь вы можете войти', 'success')
            return redirect(url_for('auth.login'))  # Перенаправляем на страницу входа
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {str(e)}")
            db.session.rollback()
            flash('Произошла ошибка при регистрации', 'error')

    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем его на главную страницу
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        try:
            # Проверяем наличие пользователя и правильность пароля
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user, remember=remember)
                logger.info(f"Пользователь {username} успешно вошел в систему")
                return redirect(url_for('main.index'))  # Перенаправляем на главную страницу

            flash('Неверное имя пользователя или пароль', 'error')
        except Exception as e:
            logger.error(f"Ошибка при входе пользователя: {str(e)}")
            flash('Произошла ошибка при входе в систему', 'error')

    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    try:
        username = current_user.username
        logout_user()
        logger.info(f"Пользователь {username} вышел из системы")
        flash('Вы успешно вышли из системы', 'info')
    except Exception as e:
        logger.error(f"Ошибка при выходе из системы: {str(e)}")
        flash('Произошла ошибка при выходе из системы', 'error')

    return redirect(url_for('auth.login'))