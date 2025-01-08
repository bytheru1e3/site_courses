from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from enum import Enum

class NotificationType(Enum):
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    courses = db.relationship('Course', backref='author', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not password:
            return False
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        self.last_login = datetime.utcnow()

    def get_unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def __repr__(self):
        return f'<User {self.username}>'

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False, default=NotificationType.INFO.value)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    materials = db.relationship('Material', backref='course', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Course {self.title}>'

class Material(db.Model):
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    vector = db.Column(db.Text)  # Для хранения векторных эмбеддингов

    # Relationships
    files = db.relationship('MaterialFile', backref='material', lazy=True, cascade='all, delete-orphan')

    def set_vector(self, vector_data):
        self.vector = json.dumps(vector_data)

    def get_vector(self):
        return json.loads(self.vector) if self.vector else None

class MaterialFile(db.Model):
    __tablename__ = 'material_files'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_indexed = db.Column(db.Boolean, default=False)
    vector = db.Column(db.Text)

    def set_vector(self, vector_data):
        self.vector = json.dumps(vector_data)
        self.is_indexed = True

    def get_vector(self):
        return json.loads(self.vector) if self.vector else None