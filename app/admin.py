from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, Course, Material, MaterialFile
from app import db
import logging
from functools import wraps

logger = logging.getLogger(__name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('У вас нет прав для доступа к этой странице', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@login_required
@admin_required
def index():
    """Главная страница административной панели"""
    stats = {
        'users_count': User.query.count(),
        'courses_count': Course.query.count(),
        'materials_count': Material.query.count(),
        'files_count': MaterialFile.query.count()
    }
    return render_template('admin/index.html', stats=stats)

@admin.route('/users')
@login_required
@admin_required
def users():
    """Список всех пользователей"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin.route('/courses')
@login_required
@admin_required
def courses():
    """Список всех курсов"""
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('admin/courses.html', courses=courses)

@admin.route('/files')
@login_required
@admin_required
def files():
    """Список всех файлов"""
    files = MaterialFile.query.order_by(MaterialFile.uploaded_at.desc()).all()
    return render_template('admin/files.html', files=files)