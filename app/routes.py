from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, login_user, logout_user, current_user
from app.models import User, Course, Material
from app import db
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

@main.route('/')
@login_required
def index():
    try:
        logger.debug(f"[INDEX] User authenticated: {current_user.is_authenticated}")
        logger.debug(f"[INDEX] User ID: {current_user.get_id()}")
        logger.debug(f"[INDEX] Session data: {session}")
        courses = Course.query.order_by(Course.created_at.desc()).all()
        return render_template('index.html', courses=courses)
    except Exception as e:
        logger.error(f"[INDEX] Error in index route: {e}")
        flash('Произошла ошибка при загрузке курсов', 'error')
        return redirect(url_for('auth.login'))

@main.route('/course/<int:course_id>')
@login_required
def course(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course.html', course=course)

@main.route('/material/<int:material_id>')
@login_required
def material(material_id):
    material = Material.query.get_or_404(material_id)
    return render_template('material.html', material=material)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logger.debug("[LOGIN] User is already authenticated")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        try:
            # Сначала находим пользователя по username
            user_by_username = User.query.filter_by(username=username).first()
            logger.debug(f"[LOGIN] Found user by username: {user_by_username is not None}")

            if user_by_username:
                # Затем получаем пользователя по id для окончательной проверки
                user = User.query.filter_by(id=user_by_username.id).first()
                logger.debug(f"[LOGIN] Found user by id: {user is not None}")

                if user and user.check_password(password):
                    login_user(user, remember=remember)
                    session.permanent = True

                    logger.debug(f"[LOGIN] User {username} logged in successfully")
                    logger.debug(f"[LOGIN] User authenticated: {current_user.is_authenticated}")
                    logger.debug(f"[LOGIN] Session: {session}")

                    next_page = request.args.get('next')
                    if not next_page or next_page == url_for('auth.login'):
                        next_page = url_for('main.index')

                    logger.debug(f"[LOGIN] Redirecting to: {next_page}")
                    flash('Вы успешно вошли в систему', 'success')
                    return redirect(next_page)

            flash('Неверное имя пользователя или пароль', 'error')
            logger.warning(f"[LOGIN] Failed login attempt for username: {username}")

        except Exception as e:
            logger.error(f"[LOGIN] Error during login process: {e}")
            flash('Произошла ошибка при попытке входа', 'error')

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    try:
        username = current_user.username
        logout_user()
        session.clear()
        logger.info(f"[LOGOUT] User {username} logged out successfully")
        flash('Вы успешно вышли из системы', 'info')
    except Exception as e:
        logger.error(f"[LOGOUT] Error during logout: {e}")
        flash('Произошла ошибка при выходе из системы', 'error')

    return redirect(url_for('auth.login'))