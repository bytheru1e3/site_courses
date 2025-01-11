from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from app.models import Course, Material, MaterialFile, User, Notification
from app import db
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

@main.route('/course/<int:course_id>')
def course(course_id):
    """Просмотр курса"""
    course = Course.query.get_or_404(course_id)
    return render_template('course/view.html', course=course)

@main.route('/chat')
def chat():
    """Страница чата с ИИ"""
    try:
        # Получаем все доступные курсы
        available_courses = Course.query.all()
        return render_template('chat/index.html', courses=available_courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке страницы чата: {str(e)}")
        flash('Произошла ошибка при загрузке чата', 'error')
        return redirect(url_for('main.index'))

@main.route('/chat/ask', methods=['POST'])
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
        # Получаем ответ на вопрос
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