from flask import Blueprint, render_template, redirect, url_for, request
from app.models import Course, Material
from app import db
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

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