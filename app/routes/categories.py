from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.utils.decorators import role_required
from app import db
from app.models import Category

bp = Blueprint('categories', __name__, url_prefix='/api/categories')

@bp.route('', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_category():
    try:
        data = request.get_json()
        category = Category(name=data['name'], description=data.get('description'))
        db.session.add(category)
        db.session.commit()
        return jsonify({'message': 'Category created', 'category_id': category.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Category error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.filter_by(is_active=True).all()
        
        return jsonify({
            'categories': [{
                'id': c.id,
                'name': c.name,
                'description': c.description
            } for c in categories]
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get categories'}), 500
