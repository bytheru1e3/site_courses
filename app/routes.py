from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_from_directory
from app.models import Course, Material, MaterialFile, User, Notification
from app import db
import logging
from app.services.file_processor import FileProcessor
import os
import shutil
from app.services.notification_service import NotificationService
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """
    Главная страница с админ-панелью
    """
    stats = {
        'users_count': User.query.count(),
        'courses_count': Course.query.count(),
        'materials_count': Material.query.count(),
        'files_count': MaterialFile.query.count()
    }
    return render_template('admin/index.html', stats=stats, is_admin=True)

@main.route('/course/<int:course_id>/manage_access', methods=['GET', 'POST'])
def manage_course_access(course_id):
    """Управление доступом пользователей к курсу"""
    try:
        course = Course.query.get_or_404(course_id)

        if request.method == 'POST':
            user_id = request.form.get('user_id')
            action = request.form.get('action')

            if not user_id or not action:
                flash('Неверные параметры запроса', 'error')
                return redirect(url_for('main.manage_course_access', course_id=course_id))

            user = User.query.get_or_404(user_id)

            if action == 'grant':
                if not user.has_access_to_course(course):
                    user.available_courses.append(course)
                    db.session.commit()
                    flash(f'Доступ предоставлен пользователю {user.username}', 'success')
            elif action == 'revoke':
                if user.has_access_to_course(course):
                    user.available_courses.remove(course)
                    db.session.commit()
                    flash(f'Доступ отозван у пользователя {user.username}', 'success')

        # Получаем список всех пользователей для управления доступом
        users = User.query.filter_by(is_admin=False).all()
        return render_template('course/manage_access.html', course=course, users=users)

    except Exception as e:
        logger.error(f"Ошибка при управлении доступом к курсу: {str(e)}")
        flash('Произошла ошибка при управлении доступом', 'error')
        return redirect(url_for('main.index'))

@main.route('/course/<int:course_id>')
def course(course_id):
    """Просмотр курса"""
    course = Course.query.get_or_404(course_id)
    return render_template('course/view.html', course=course)

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
def add_course():
    """Добавление нового курса"""
    try:
        title = request.form.get('title')
        description = request.form.get('description')

        if not title:
            flash('Название курса обязательно', 'error')
            return redirect(url_for('main.index'))

        # Получаем текущего пользователя через flask-login
        if current_user and current_user.is_authenticated:
            user_id = current_user.id
        else:
            # Если пользователь не аутентифицирован, используем системного пользователя
            system_user = User.query.filter_by(username='system').first()
            if not system_user:
                system_user = User(
                    username='system',
                    email='system@example.com',
                    is_admin=True
                )
                system_user.set_password('system')
                db.session.add(system_user)
                db.session.commit()
            user_id = system_user.id

        course = Course(
            title=title,
            description=description,
            user_id=user_id
        )

        db.session.add(course)
        db.session.commit()

        logger.info(f"Создан новый курс: {title}")
        flash('Курс успешно создан', 'success')

    except Exception as e:
        logger.error(f"Ошибка при создании курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при создании курса', 'error')

    return redirect(url_for('main.index'))

@main.route('/edit_course/<int:course_id>', methods=['POST'])
def edit_course(course_id):
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
def delete_course(course_id):
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
def material(material_id):
    material = Material.query.get_or_404(material_id)
    return render_template('material.html', material=material)

@main.route('/add_material/<int:course_id>', methods=['POST'])
def add_material(course_id):
    title = request.form.get('title')
    content = request.form.get('content')

    material = Material(course_id=course_id, title=title, content=content)
    db.session.add(material)
    db.session.commit()

    return redirect(url_for('main.course', course_id=course_id))

@main.route('/edit_material/<int:material_id>', methods=['POST'])
def edit_material(material_id):
    material = Material.query.get_or_404(material_id)
    material.title = request.form.get('title')
    material.content = request.form.get('content')
    db.session.commit()
    return redirect(url_for('main.material', material_id=material_id))

@main.route('/delete_material/<int:material_id>', methods=['POST'])
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    course_id = material.course_id

    for material_file in material.files:
        delete_material_file(material_file.id)

    db.session.delete(material)
    db.session.commit()
    return redirect(url_for('main.course', course_id=course_id))

@main.route('/upload_file/<int:material_id>', methods=['POST'])
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

            material_folder = os.path.join(UPLOAD_FOLDER, str(material_id))
            os.makedirs(material_folder, exist_ok=True)

            file_path = os.path.join(material_folder, filename)
            file.save(file_path)

            material_file = MaterialFile(
                material_id=material_id,
                filename=filename,
                file_path=os.path.join(str(material_id), filename),
                file_type=file_type
            )
            db.session.add(material_file)
            db.session.commit()

            if process_and_index_file(material_file):
                flash('Файл успешно загружен и проиндексирован', 'success')
            else:
                flash('Файл загружен, но возникла ошибка при индексации', 'warning')

        except Exception as e:
            logger.error(f"Ошибка при загрузке файла: {str(e)}")
            flash('Произошла ошибка при загрузке файла', 'error')

    return redirect(url_for('main.material', material_id=material_id))

@main.route('/delete_file/<int:file_id>', methods=['POST'])
def delete_material_file(file_id):
    material_file = MaterialFile.query.get_or_404(file_id)
    try:
        file_path = os.path.join(UPLOAD_FOLDER, material_file.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

        material_folder = os.path.dirname(file_path)
        if not os.listdir(material_folder):
            shutil.rmtree(material_folder)

        vector_db = FileProcessor.get_vector_db()
        vector_db.remove_document(file_path)

        db.session.delete(material_file)
        db.session.commit()

        flash('Файл успешно удален', 'success')
    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {str(e)}")
        flash('Произошла ошибка при удалении файла', 'error')

    return redirect(url_for('main.material', material_id=material_file.material_id))

@main.route('/reindex_file/<int:file_id>', methods=['POST'])
def reindex_file(file_id):
    material_file = MaterialFile.query.get_or_404(file_id)
    if process_and_index_file(material_file):
        flash('Файл успешно переиндексирован', 'success')
    else:
        flash('Произошла ошибка при переиндексации файла', 'error')
    return redirect(url_for('main.material', material_id=material_file.material_id))

@main.route('/download_file/<int:file_id>')
def download_file(file_id):
    material_file = MaterialFile.query.get_or_404(file_id)
    return send_from_directory(UPLOAD_FOLDER, material_file.file_path)


@main.route('/notifications')
def notifications():
    """Просмотр всех уведомлений"""
    try:
        # Получаем все активные уведомления для текущего пользователя
        if current_user and current_user.is_authenticated:
            notifications = Notification.query.filter_by(
                user_id=current_user.id,
                is_deleted=False
            ).order_by(Notification.created_at.desc()).all()
        else:
            notifications = []

        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        logger.error(f"Ошибка при получении уведомлений: {str(e)}")
        flash('Произошла ошибка при загрузке уведомлений', 'error')
        return redirect(url_for('main.index'))

@main.route('/notifications/unread')
def get_unread_notifications():
    """Получение непрочитанных уведомлений"""
    return jsonify([])  # Пустой список для демонстрации

@main.route('/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Отметка уведомления как прочитанного"""
    return jsonify({'success': True})

@main.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """Отметка всех уведомлений как прочитанных"""
    return jsonify({'success': True})

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'docx', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from flask import send_from_directory

@main.route('/admin/users/add', methods=['POST'])
def add_user():
    """Добавление нового пользователя"""
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = bool(request.form.get('is_admin'))

        # Проверка существования пользователя
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return redirect(url_for('admin.users'))

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return redirect(url_for('admin.users'))

        # Создание пользователя
        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Пользователь успешно создан', 'success')
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при создании пользователя', 'error')

    return redirect(url_for('admin.users'))