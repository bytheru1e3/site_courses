from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models import Course, Material, MaterialFile, User, Notification
from app import db
from werkzeug.security import generate_password_hash
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """
    Главная страница с админ-панелью
    """
    courses = Course.query.all()
    return render_template('index.html', courses=courses)

@main.route('/add_user', methods=['POST'])
@login_required
def add_user():
    """Добавление нового пользователя через админ-панель"""
    if not current_user.is_admin:
        flash('У вас нет доступа к этой функции', 'error')
        return redirect(url_for('main.index'))

    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = bool(request.form.get('is_admin'))

        if not all([username, email, password]):
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('admin.users'))

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('admin.users'))

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('admin.users'))

        new_user = User(
            username=username,
            email=email,
            is_admin=is_admin
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Пользователь успешно создан', 'success')
        return redirect(url_for('admin.users'))

    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при создании пользователя', 'error')
        return redirect(url_for('admin.users'))

@main.route('/add_course', methods=['POST'])
@login_required
def add_course():
    """Добавление нового курса"""
    try:
        title = request.form.get('title')
        description = request.form.get('description')

        if not title:
            flash('Название курса обязательно', 'error')
            return redirect(url_for('main.index'))

        new_course = Course(
            title=title,
            description=description,
            user_id=current_user.id
        )
        db.session.add(new_course)
        db.session.commit()

        flash('Курс успешно создан', 'success')
        return redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"Ошибка при создании курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при создании курса', 'error')
        return redirect(url_for('main.index'))

@main.route('/course/<int:course_id>')
@login_required
def course(course_id):
    """Просмотр курса"""
    course = Course.query.get_or_404(course_id)
    return render_template('course/view.html', course=course)

@main.route('/chat')
@login_required
def chat():
    """Страница чата с ИИ"""
    try:
        available_courses = Course.query.all()
        return render_template('chat/index.html', courses=available_courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке страницы чата: {str(e)}")
        flash('Произошла ошибка при загрузке чата', 'error')
        return redirect(url_for('main.index'))

@main.route('/chat/ask', methods=['POST'])
@login_required
def ask_question():
    """Обработка вопроса к ИИ"""
    try:
        question = request.form.get('question')

        if not question:
            return jsonify({
                'success': False,
                'error': 'Необходимо задать вопрос'
            }), 400

        vector_db_path = "app/data"
        from app.ai import answer_question
        response = answer_question(question, vector_db_path)

        return jsonify({
            'success': True,
            'answer': response
        })

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Произошла ошибка при обработке вопроса'
        }), 500

@main.route('/notifications')
@login_required
def notifications():
    """Страница уведомлений пользователя"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_deleted=False
        ).order_by(Notification.created_at.desc()).all()
        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        logger.error(f"Ошибка при загрузке уведомлений: {str(e)}")
        flash('Произошла ошибка при загрузке уведомлений', 'error')
        return redirect(url_for('main.index'))

@main.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    """Удаление курса"""
    if not current_user.is_admin:
        flash('У вас нет доступа к этой функции', 'error')
        return redirect(url_for('main.index'))

    try:
        course = Course.query.get_or_404(course_id)
        db.session.delete(course)
        db.session.commit()
        flash('Курс успешно удален', 'success')
    except Exception as e:
        logger.error(f"Ошибка при удалении курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при удалении курса', 'error')

    return redirect(url_for('admin.courses'))