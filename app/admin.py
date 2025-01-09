from flask import Blueprint, render_template, flash, redirect, url_for
from app.models import User, Course, Material, MaterialFile
from app import db
import logging

logger = logging.getLogger(__name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/')
def index():
    """Главная страница административной панели"""
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
def users():
    """Список всех пользователей"""
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка пользователей: {str(e)}")
        flash('Ошибка при загрузке списка пользователей', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/courses')
def courses():
    """Список всех курсов"""
    try:
        courses = Course.query.order_by(Course.created_at.desc()).all()
        return render_template('admin/courses.html', courses=courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка курсов: {str(e)}")
        flash('Ошибка при загрузке списка курсов', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/files')
def files():
    """Список всех файлов"""
    try:
        files = MaterialFile.query.order_by(MaterialFile.uploaded_at.desc()).all()
        return render_template('admin/files.html', files=files)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка файлов: {str(e)}")
        flash('Ошибка при загрузке списка файлов', 'error')
        return redirect(url_for('admin.index'))