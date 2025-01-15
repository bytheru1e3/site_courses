from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file
from app.models import Course, Material, MaterialFile, User, Notification
from app import db
import logging
import os
from werkzeug.utils import secure_filename
from app.services.file_processor import FileProcessor

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """
    Главная страница со списком курсов
    """
    try:
        courses = Course.query.all()
        return render_template('index.html', courses=courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка курсов: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return render_template('index.html', courses=[])

@main.route('/users')
def users():
    """Страница управления пользователями"""
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка пользователей: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return render_template('admin/users.html', users=[])

@main.route('/materials')
def materials():
    """Страница управления материалами"""
    try:
        materials = Material.query.all()
        return render_template('admin/materials.html', materials=materials)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка материалов: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return render_template('admin/materials.html', materials=[])

@main.route('/files')
def files():
    """Страница управления файлами"""
    try:
        files = MaterialFile.query.all()
        return render_template('admin/files.html', files=files)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка файлов: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return render_template('admin/files.html', files=[])

@main.route('/course/<int:course_id>')
def course(course_id):
    """Просмотр курса"""
    try:
        course = Course.query.get_or_404(course_id)
        return render_template('course/view.html', course=course)
    except Exception as e:
        logger.error(f"Ошибка при загрузке курса: {str(e)}")
        flash('Произошла ошибка при загрузке курса', 'error')
        return redirect(url_for('main.index'))

@main.route('/course/<int:course_id>/edit', methods=['POST'])
def edit_course(course_id):
    """Редактирование курса"""
    try:
        course = Course.query.get_or_404(course_id)
        title = request.form.get('title')
        description = request.form.get('description', '')

        if not title:
            flash('Название курса обязательно', 'error')
            return redirect(url_for('main.course', course_id=course_id))

        course.title = title
        course.description = description
        db.session.commit()

        flash('Курс успешно обновлен', 'success')
        return redirect(url_for('main.course', course_id=course_id))

    except Exception as e:
        logger.error(f"Ошибка при редактировании курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при редактировании курса', 'error')
        return redirect(url_for('main.index'))

@main.route('/course/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    """Удаление курса"""
    try:
        course = Course.query.get_or_404(course_id)

        # Удаляем все файлы курса физически
        for material in course.materials:
            for file in material.files:
                if os.path.exists(file.file_path):
                    os.remove(file.file_path)

        db.session.delete(course)
        db.session.commit()

        flash('Курс и все связанные материалы успешно удалены', 'success')
        return redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"Ошибка при удалении курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при удалении курса', 'error')
        return redirect(url_for('main.index'))

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
            return redirect(url_for('main.index'))

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('main.index'))

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('main.index'))

        new_user = User(
            username=username,
            email=email,
            is_admin=is_admin
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Пользователь успешно создан', 'success')
        return redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при создании пользователя', 'error')
        return redirect(url_for('main.index'))

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
        for file in material.files:
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
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


@main.route('/material/<int:material_id>')
def material(material_id):
    """Просмотр материала"""
    try:
        material = Material.query.get_or_404(material_id)
        return render_template('material.html', material=material)
    except Exception as e:
        logger.error(f"Ошибка при загрузке материала: {str(e)}")
        flash('Произошла ошибка при загрузке материала', 'error')
        return redirect(url_for('main.index'))

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
            file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

            if file_type not in ['pdf', 'docx']:
                flash('Неподдерживаемый тип файла. Разрешены только PDF и DOCX', 'error')
                return redirect(url_for('main.course', course_id=material.course_id))

            file_dir = os.path.join(os.getcwd(), 'app', 'uploads', str(material_id))
            os.makedirs(file_dir, exist_ok=True)

            file_path = os.path.join(file_dir, filename)
            file.save(file_path)

            material_file = MaterialFile(
                filename=filename,
                file_path=file_path,
                file_type=file_type,
                material=material,
                is_indexed=False
            )
            db.session.add(material_file)
            db.session.commit()

            try:
                vector_db_path = os.path.join(os.getcwd(), "app", "data")
                file_processor = FileProcessor(vector_db_path)

                logger.info(f"Processing file {file_path} for indexing")
                if file_processor.process_file(file_path):
                    material_file.is_indexed = True
                    db.session.commit()
                    flash('Файл успешно загружен и проиндексирован', 'success')
                    logger.info(f"File {file_path} successfully indexed")
                else:
                    flash('Файл загружен, но возникла ошибка при индексации', 'warning')
                    logger.error(f"Failed to index file {file_path}")
            except Exception as e:
                logger.error(f"Error during file indexing: {str(e)}", exc_info=True)
                flash('Файл загружен, но возникла ошибка при индексации', 'warning')

            return redirect(url_for('main.course', course_id=material.course_id))

    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}", exc_info=True)
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