from flask import Blueprint, jsonify
from flask_login import current_user
from app.models import Course

api = Blueprint('api', __name__)

@api.route('/api/courses', methods=['GET'])
def get_courses():
    """Get all available courses"""
    try:
        courses = Course.query.all()
        return jsonify({
            'success': True,
            'courses': [
                {
                    'id': course.id,
                    'title': course.title,
                    'description': course.description
                } for course in courses
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """Get specific course details"""
    try:
        course = Course.query.get_or_404(course_id)
        return jsonify({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'materials': [
                    {
                        'id': material.id,
                        'title': material.title,
                        'content': material.content
                    } for material in course.materials
                ]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
