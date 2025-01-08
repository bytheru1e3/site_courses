from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, login_user, logout_user, current_user
from app.models import User, Course, Material
from app import db
from app.services.vector_search import VectorSearch
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
vector_search = VectorSearch()

@main.route('/')
@login_required
def index():
    try:
        logger.debug(f"User accessing index page: {current_user.username}")
        courses = Course.query.order_by(Course.created_at.desc()).all()
        return render_template('index.html', courses=courses)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        flash('Произошла ошибка при загрузке курсов', 'error')
        return redirect(url_for('auth.login'))

@main.route('/course/<int:course_id>')
@login_required
def course(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course.html', course=course)

@main.route('/course/add', methods=['GET', 'POST'])
@login_required
def add_course():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('main.index'))
            
        course = Course(title=title, description=description)
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully')
        return redirect(url_for('main.index'))
    
    return render_template('course.html', course=None)

@main.route('/material/<int:material_id>')
@login_required
def material(material_id):
    material = Material.query.get_or_404(material_id)
    return render_template('material.html', material=material)

@main.route('/material/add/<int:course_id>', methods=['POST'])
@login_required
def add_material():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        course_id = request.form.get('course_id')
        
        if not all([title, content, course_id]):
            flash('All fields are required', 'error')
            return redirect(url_for('main.course', course_id=course_id))
            
        material = Material(title=title, content=content, course_id=course_id)
        # Создаем векторное представление для материала
        vector = vector_search.create_embedding(content)
        material.set_vector(vector)
        
        db.session.add(material)
        db.session.commit()
        flash('Material added successfully')
        return redirect(url_for('main.course', course_id=course_id))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated:
        logger.debug(f"Already authenticated user {current_user.username} accessing login page")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                # Успешная авторизация
                login_user(user, remember=True)
                logger.info(f"User {username} logged in successfully")

                # Получаем next параметр для редиректа
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('main.index')

                return redirect(next_page)

            # Неверные учетные данные
            flash('Неверное имя пользователя или пароль', 'error')
            logger.warning(f"Failed login attempt for username: {username}")

        except Exception as e:
            logger.error(f"Error during login process: {e}")
            flash('Произошла ошибка при попытке входа', 'error')

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    try:
        username = current_user.username
        logout_user()
        logger.info(f"User {username} logged out successfully")
        flash('Вы успешно вышли из системы', 'info')
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        flash('Произошла ошибка при выходе из системы', 'error')

    return redirect(url_for('auth.login'))