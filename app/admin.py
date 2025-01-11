from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, Course, Material, MaterialFile
from app import db
import logging

logger = logging.getLogger(__name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
@login_required
def index():
    """Главная страница административной панели"""
    if not current_user.is_admin:
        flash('У вас нет доступа к административной панели', 'error')
        return redirect(url_for('main.index'))

    try:
        stats = {
            'users_count': User.query.count(),
            'courses_count': Course.query.count(),
            'materials_count': Material.query.count(),
            'files_count': MaterialFile.query.count()
        }
        return render_template('admin/index.html', stats=stats)
    except Exception as e:
        logger.error(f"Ошибка при загрузке статистики: {str(e)}")
        flash('Ошибка при загрузке статистики', 'error')
        return redirect(url_for('main.index'))

@admin.route('/users')
@login_required
def users():
    """Список всех пользователей"""
    if not current_user.is_admin:
        flash('У вас нет доступа к административной панели', 'error')
        return redirect(url_for('main.index'))

    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка пользователей: {str(e)}")
        flash('Ошибка при загрузке списка пользователей', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/courses')
@login_required
def courses():
    """Список всех курсов"""
    if not current_user.is_admin:
        flash('У вас нет доступа к административной панели', 'error')
        return redirect(url_for('main.index'))

    try:
        courses = Course.query.order_by(Course.created_at.desc()).all()
        return render_template('admin/courses.html', courses=courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка курсов: {str(e)}")
        flash('Ошибка при загрузке списка курсов', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/files')
@login_required
def files():
    """Список всех файлов"""
    if not current_user.is_admin:
        flash('У вас нет доступа к административной панели', 'error')
        return redirect(url_for('main.index'))

    try:
        files = MaterialFile.query.order_by(MaterialFile.uploaded_at.desc()).all()
        return render_template('admin/files.html', files=files)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка файлов: {str(e)}")
        flash('Ошибка при загрузке списка файлов', 'error')
        return redirect(url_for('admin.index'))