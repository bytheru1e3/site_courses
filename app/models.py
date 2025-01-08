from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    materials = db.relationship('Material', backref='course', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }

class Material(db.Model):
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text)
    vector = db.Column(db.Text)  # Хранение векторных эмбеддингов
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_vector(self, vector_data):
        self.vector = json.dumps(vector_data)

    def get_vector(self):
        return json.loads(self.vector) if self.vector else None

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.String(32), nullable=False)
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)