from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from app.models import Course, Material, MaterialFile, User, Notification
from app import db
import logging
import os
from werkzeug.utils import secure_filename #Import secure_filename

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
def add_user():
    """Добавление нового пользователя через админ-панель"""
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
def add_course():
    """Добавление нового курса"""
    try:
        title = request.form.get('title')
        description = request.form.get('description', '')

        if not title:
            flash('Название курса обязательно', 'error')
            return redirect(url_for('main.index'))

        new_course = Course(
            title=title,
            description=description
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
def course(course_id):
    """Просмотр курса"""
    course = Course.query.get_or_404(course_id)
    return render_template('course/view.html', course=course)

@main.route('/course/<int:course_id>/add_material', methods=['POST'])
def add_material(course_id):
    """Добавление материала к курсу"""
    try:
        course = Course.query.get_or_404(course_id)
        title = request.form.get('title')
        content = request.form.get('content', '')

        if not title:
            flash('Название материала обязательно', 'error')
            return redirect(url_for('main.course', course_id=course_id))

        material = Material(
            title=title,
            content=content,
            course=course
        )
        db.session.add(material)
        db.session.commit()

        flash('Материал успешно добавлен', 'success')
        return redirect(url_for('main.course', course_id=course_id))

    except Exception as e:
        logger.error(f"Ошибка при добавлении материала: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при добавлении материала', 'error')
        return redirect(url_for('main.course', course_id=course_id))

@main.route('/material/<int:material_id>/edit', methods=['POST'])
def edit_material(material_id):
    """Редактирование материала"""
    try:
        material = Material.query.get_or_404(material_id)
        title = request.form.get('title')
        content = request.form.get('content', '')

        if not title:
            flash('Название материала обязательно', 'error')
            return redirect(url_for('main.course', course_id=material.course_id))

        material.title = title
        material.content = content
        db.session.commit()

        flash('Материал успешно обновлен', 'success')
        return redirect(url_for('main.course', course_id=material.course_id))

    except Exception as e:
        logger.error(f"Ошибка при редактировании материала: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при редактировании материала', 'error')
        return redirect(url_for('main.course', course_id=material.course_id))

@main.route('/material/<int:material_id>/delete', methods=['POST'])
def delete_material(material_id):
    """Удаление материала"""
    try:
        material = Material.query.get_or_404(material_id)
        course_id = material.course_id
        db.session.delete(material)
        db.session.commit()

        flash('Материал успешно удален', 'success')
        return redirect(url_for('main.course', course_id=course_id))

    except Exception as e:
        logger.error(f"Ошибка при удалении материала: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при удалении материала', 'error')
        return redirect(url_for('main.course', course_id=material.course_id))

@main.route('/chat')
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
def ask_question():
    """Обработка вопроса к ИИ"""
    try:
        question = request.form.get('question')

        if not question:
            return jsonify({
                'success': False,
                'error': 'Необходимо задать вопрос'
            }), 400

        vector_db_path = os.path.join(os.getcwd(), "app", "data")
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
def notifications():
    """Страница уведомлений"""
    try:
        notifications = Notification.query.filter_by(
            is_deleted=False
        ).order_by(Notification.created_at.desc()).all()
        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        logger.error(f"Ошибка при загрузке уведомлений: {str(e)}")
        flash('Произошла ошибка при загрузке уведомлений', 'error')
        return redirect(url_for('main.index'))

@main.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    """Удаление курса"""
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


@main.route('/material/<int:material_id>/upload_file', methods=['POST'])
def upload_file(material_id):
    """Загрузка файла к материалу с добавлением в векторную БД"""
    try:
        material = Material.query.get_or_404(material_id)
        if 'file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(url_for('main.course', course_id=material.course_id))

        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(url_for('main.course', course_id=material.course_id))

        if file:
            filename = secure_filename(file.filename)
            # Создаем директорию для файлов материала если её нет
            file_dir = os.path.join(os.getcwd(), 'app', 'uploads', str(material_id))
            os.makedirs(file_dir, exist_ok=True)

            file_path = os.path.join(file_dir, filename)
            file.save(file_path)

            # Создаем запись о файле в БД
            material_file = MaterialFile(
                filename=filename,
                file_path=file_path,
                material=material
            )
            db.session.add(material_file)
            db.session.commit()

            # Добавляем файл в векторную БД (Предполагается, что функция существует)
            from app.ai import add_file_to_vector_db #Import add_file_to_vector_db
            vector_db_path = os.path.join(os.getcwd(), "app", "data")
            success = add_file_to_vector_db(file_path, vector_db_path)

            if success:
                flash('Файл успешно загружен и обработан', 'success')
            else:
                flash('Файл загружен, но возникла ошибка при обработке', 'warning')

            return redirect(url_for('main.course', course_id=material.course_id))

    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при загрузке файла', 'error')
        return redirect(url_for('main.course', course_id=material.course_id))

@main.route('/file/<int:file_id>/download')
def download_file(file_id):
    """Скачивание файла"""
    try:
        file = MaterialFile.query.get_or_404(file_id)
        return send_file(file.file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла: {str(e)}")
        flash('Произошла ошибка при скачивании файла', 'error')
        return redirect(url_for('main.course', course_id=file.material.course_id))

@main.route('/file/<int:file_id>/delete', methods=['POST'])
def delete_file(file_id):
    """Удаление файла"""
    try:
        file = MaterialFile.query.get_or_404(file_id)
        course_id = file.material.course_id

        # Удаляем физический файл
        if os.path.exists(file.file_path):
            os.remove(file.file_path)

        db.session.delete(file)
        db.session.commit()

        flash('Файл успешно удален', 'success')
        return redirect(url_for('main.course', course_id=course_id))

    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при удалении файла', 'error')
        return redirect(url_for('main.course', course_id=file.material.course_id))