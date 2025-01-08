from flask import Blueprint, render_template, redirect, url_for, request, send_from_directory, current_app
from werkzeug.utils import secure_filename
from app.models import Course, Material, MaterialFile # Assumed MaterialFile model exists
from app import db
import logging
import os

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

# Создаем директорию для загруженных файлов
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'docx', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/')
def index():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('index.html', courses=courses)

@main.route('/course/<int:course_id>')
def course(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course.html', course=course)

@main.route('/material/<int:material_id>')
def material(material_id):
    material = Material.query.get_or_404(material_id)
    return render_template('material.html', material=material)

@main.route('/add_course', methods=['POST'])
def add_course():
    title = request.form.get('title')
    description = request.form.get('description')

    course = Course(title=title, description=description)
    db.session.add(course)
    db.session.commit()

    return redirect(url_for('main.index'))

@main.route('/add_material/<int:course_id>', methods=['POST'])
def add_material(course_id):
    title = request.form.get('title')
    content = request.form.get('content')

    material = Material(course_id=course_id, title=title, content=content)
    db.session.add(material)
    db.session.commit()

    return redirect(url_for('main.course', course_id=course_id))

@main.route('/upload_file/<int:material_id>', methods=['POST'])
def upload_file(material_id):
    if 'file' not in request.files:
        return redirect(url_for('main.material', material_id=material_id))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('main.material', material_id=material_id))

    if file and allowed_file(file.filename):
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

    return redirect(url_for('main.material', material_id=material_id))

@main.route('/download_file/<int:file_id>')
def download_file(file_id):
    material_file = MaterialFile.query.get_or_404(file_id)
    return send_from_directory(UPLOAD_FOLDER, material_file.file_path)