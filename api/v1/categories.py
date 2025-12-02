"""Categories API endpoints"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.category import Category
from src.extensions import db
from schemas import category_schema, categories_schema

# Create namespace
ns = Namespace('categories', description='Category operations')

# Define request/response models
category_model = ns.model('Category', {
    'name': fields.String(required=True, description='Category name'),
    'icon': fields.String(description='Category icon class (e.g., fa-home)'),
    'parent_id': fields.Integer(description='Parent category ID for subcategories'),
})


@ns.route('/')
class CategoryList(Resource):
    @ns.doc('list_categories', security='Bearer')
    @jwt_required()
    def get(self):
        """Get all categories for current user"""
        current_user_id = get_jwt_identity()

        # Get all categories (including parent/subcategories)
        categories = Category.query.filter_by(user_id=current_user_id).all()

        # Serialize
        result = categories_schema.dump(categories)

        return {
            'success': True,
            'categories': result
        }, 200

    @ns.doc('create_category', security='Bearer')
    @ns.expect(category_model)
    def post(self):
        """Create a new category"""
        current_user_id = get_jwt_identity()
        data = request.get_json()

        try:
            new_category = Category(
                name=data.get('name'),
                icon=data.get('icon', 'fa-tag'),
                parent_id=data.get('parent_id'),
                user_id=current_user_id
            )

            db.session.add(new_category)
            db.session.commit()

            result = category_schema.dump(new_category)

            return {
                'success': True,
                'category': result,
                'message': 'Category created successfully'
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>')
@ns.param('id', 'Category ID')
class CategoryDetail(Resource):
    @ns.doc('get_category', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get a specific category by ID"""
        current_user_id = get_jwt_identity()

        category = Category.query.filter_by(id=id, user_id=current_user_id).first()

        if not category:
            return {'success': False, 'error': 'Category not found'}, 404

        result = category_schema.dump(category)

        return {
            'success': True,
            'category': result
        }, 200

    @ns.doc('update_category', security='Bearer')
    @ns.expect(category_model)
    def put(self, id):
        """Update a category"""
        current_user_id = get_jwt_identity()

        category = Category.query.filter_by(id=id, user_id=current_user_id).first()

        if not category:
            return {'success': False, 'error': 'Category not found'}, 404

        data = request.get_json()

        try:
            if 'name' in data:
                category.name = data['name']
            if 'icon' in data:
                category.icon = data['icon']
            if 'parent_id' in data:
                category.parent_id = data['parent_id']

            db.session.commit()

            result = category_schema.dump(category)

            return {
                'success': True,
                'category': result,
                'message': 'Category updated successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400

    @ns.doc('delete_category', security='Bearer')
    def delete(self, id):
        """Delete a category"""
        current_user_id = get_jwt_identity()

        category = Category.query.filter_by(id=id, user_id=current_user_id).first()

        if not category:
            return {'success': False, 'error': 'Category not found'}, 404

        try:
            db.session.delete(category)
            db.session.commit()

            return {
                'success': True,
                'message': 'Category deleted successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400
