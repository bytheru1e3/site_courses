from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app.models import Course, Material, MaterialFile, User
from app import db
import logging
from app.services.file_processor import FileProcessor
import os
import shutil
from app.services.notification_service import NotificationService
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """
    Главная страница с списком курсов.
    Доступна всем пользователям.
    """
    try:
        logger.info("Доступ к главной странице")
        courses = Course.query.order_by(Course.created_at.desc()).all()
        is_admin = current_user.is_authenticated and current_user.is_admin

        return render_template('index.html', 
                            courses=courses, 
                            is_admin=is_admin)
    except Exception as e:
        logger.error(f"Ошибка при загрузке главной страницы: {str(e)}")
        flash('Произошла ошибка при загрузке курсов', 'error')
        return render_template('index.html', courses=[], is_admin=False)

@main.route('/course/<int:course_id>')
@login_required
def course(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_admin and course.user_id != current_user.id:
        flash('У вас нет доступа к этому курсу', 'error')
        return redirect(url_for('main.index'))
    return render_template('course.html', course=course)

def process_and_index_file(material_file):
    """Обработка и индексация файла"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, material_file.file_path)
        vector = FileProcessor.process_file(file_path)
        material_file.set_vector(vector)
        db.session.commit()
        logger.info(f"Файл {material_file.filename} успешно проиндексирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при индексации файла {material_file.filename}: {str(e)}")
        return False

@main.route('/add_course', methods=['POST'])
@login_required
def add_course():
    if not current_user.is_admin:
        flash('У вас нет прав для создания курсов', 'error')
        return redirect(url_for('main.index'))

    title = request.form.get('title')
    description = request.form.get('description')

    try:
        course = Course(
            title=title, 
            description=description,
            user_id=current_user.id
        )
        db.session.add(course)
        db.session.commit()
        flash('Курс успешно создан', 'success')
    except Exception as e:
        logger.error(f"Ошибка при создании курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при создании курса', 'error')

    return redirect(url_for('main.index'))

@main.route('/edit_course/<int:course_id>', methods=['POST'])
@login_required
def edit_course(course_id):
    if not current_user.is_admin:
        flash('У вас нет прав для редактирования курсов', 'error')
        return redirect(url_for('main.index'))

    course = Course.query.get_or_404(course_id)
    try:
        course.title = request.form.get('title')
        course.description = request.form.get('description')
        db.session.commit()
        flash('Курс успешно обновлен', 'success')
    except Exception as e:
        logger.error(f"Ошибка при обновлении курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при обновлении курса', 'error')

    return redirect(url_for('main.index'))

@main.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if not current_user.is_admin:
        flash('У вас нет прав для удаления курсов', 'error')
        return redirect(url_for('main.index'))

    course = Course.query.get_or_404(course_id)
    try:
        db.session.delete(course)
        db.session.commit()
        flash('Курс успешно удален', 'success')
    except Exception as e:
        logger.error(f"Ошибка при удалении курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при удалении курса', 'error')

    return redirect(url_for('main.index'))

@main.route('/material/<int:material_id>')
@login_required
def material(material_id):
    material = Material.query.get_or_404(material_id)
    if not current_user.is_admin and material.course.user_id != current_user.id:
        flash('У вас нет доступа к этому материалу', 'error')
        return redirect(url_for('main.index'))
    return render_template('material.html', material=material)

@main.route('/add_material/<int:course_id>', methods=['POST'])
@login_required
def add_material(course_id):
    title = request.form.get('title')
    content = request.form.get('content')

    material = Material(course_id=course_id, title=title, content=content)
    db.session.add(material)
    db.session.commit()

    return redirect(url_for('main.course', course_id=course_id))

@main.route('/edit_material/<int:material_id>', methods=['POST'])
@login_required
def edit_material(material_id):
    material = Material.query.get_or_404(material_id)
    material.title = request.form.get('title')
    material.content = request.form.get('content')
    db.session.commit()
    return redirect(url_for('main.material', material_id=material_id))

@main.route('/delete_material/<int:material_id>', methods=['POST'])
@login_required
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    course_id = material.course_id

    # Удаляем все файлы материала
    for material_file in material.files:
        delete_material_file(material_file.id)

    db.session.delete(material)
    db.session.commit()
    return redirect(url_for('main.course', course_id=course_id))

@main.route('/upload_file/<int:material_id>', methods=['POST'])
@login_required
def upload_file(material_id):
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('main.material', material_id=material_id))

    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('main.material', material_id=material_id))

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            file_type = filename.rsplit('.', 1)[1].lower()

            # Создаем поддиректорию для материала
            material_folder = os.path.join(UPLOAD_FOLDER, str(material_id))
            os.makedirs(material_folder, exist_ok=True)

            file_path = os.path.join(material_folder, filename)
            file.save(file_path)

            # Сохраняем информацию о файле в базе данных
            material_file = MaterialFile(
                material_id=material_id,
                filename=filename,
                file_path=os.path.join(str(material_id), filename),
                file_type=file_type
            )
            db.session.add(material_file)
            db.session.commit()

            # Индексируем файл
            if process_and_index_file(material_file):
                flash('Файл успешно загружен и проиндексирован', 'success')
            else:
                flash('Файл загружен, но возникла ошибка при индексации', 'warning')

        except Exception as e:
            logger.error(f"Ошибка при загрузке файла: {str(e)}")
            flash('Произошла ошибка при загрузке файла', 'error')

    return redirect(url_for('main.material', material_id=material_id))

@main.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_material_file(file_id):
    """Удаление файла материала вместе с его векторным представлением"""
    material_file = MaterialFile.query.get_or_404(file_id)
    try:
        # Удаляем физический файл
        file_path = os.path.join(UPLOAD_FOLDER, material_file.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

            # Если это был последний файл в папке материала, удаляем папку
            material_folder = os.path.dirname(file_path)
            if not os.listdir(material_folder):
                shutil.rmtree(material_folder)

        # Удаляем векторное представление
        vector_db = FileProcessor.get_vector_db()
        vector_db.remove_document(file_path)

        # Удаляем запись из базы данных
        db.session.delete(material_file)
        db.session.commit()

        flash('Файл успешно удален', 'success')
    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {str(e)}")
        flash('Произошла ошибка при удалении файла', 'error')

    return redirect(url_for('main.material', material_id=material_file.material_id))

@main.route('/reindex_file/<int:file_id>', methods=['POST'])
@login_required
def reindex_file(file_id):
    material_file = MaterialFile.query.get_or_404(file_id)
    if process_and_index_file(material_file):
        flash('Файл успешно переиндексирован', 'success')
    else:
        flash('Произошла ошибка при переиндексации файла', 'error')
    return redirect(url_for('main.material', material_id=material_file.material_id))

@main.route('/download_file/<int:file_id>')
@login_required
def download_file(file_id):
    material_file = MaterialFile.query.get_or_404(file_id)
    return send_from_directory(UPLOAD_FOLDER, material_file.file_path)


# Notifications routes
@main.route('/notifications')
@login_required
def notifications():
    """Страница со списком уведомлений пользователя"""
    notifications = NotificationService.get_user_notifications(
        current_user, 
        include_read=True,
        limit=50
    )
    return render_template('notifications.html', notifications=notifications)

@main.route('/notifications/unread')
@login_required
def get_unread_notifications():
    """Получение списка непрочитанных уведомлений"""
    notifications = NotificationService.get_user_notifications(current_user)
    return jsonify([notification.to_dict() for notification in notifications])

@main.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Отметить уведомление как прочитанное"""
    success = NotificationService.mark_as_read(notification_id, current_user.id)
    return jsonify({'success': success})

@main.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Отметить все уведомления как прочитанные"""
    NotificationService.mark_all_as_read(current_user.id)
    return jsonify({'success': True})

# Создаем директорию для загруженных файлов
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'docx', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from flask import send_from_directory