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
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('index.html', courses=courses)

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
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            logger.info(f"User {username} logged in successfully")
            return redirect(url_for('main.index'))

        flash('Неверное имя пользователя или пароль', 'error')
        logger.warning(f"Failed login attempt for username: {username}")

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))