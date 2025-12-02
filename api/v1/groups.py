"""Groups API endpoints - Bill splitting and group management"""
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.group import Group
from src.models.user import User
from src.models.associations import group_users
from src.extensions import db
from schemas import group_schema, groups_schema

# Create namespace
ns = Namespace('groups', description='Group and bill splitting operations')

# Define request/response models
group_model = ns.model('Group', {
    'name': fields.String(required=True, description='Group name'),
    'description': fields.String(description='Group description'),
    'member_ids': fields.List(fields.Integer, description='List of user IDs to add as members'),
})


@ns.route('/')
class GroupList(Resource):
    @ns.doc('list_groups', security='Bearer')
    @jwt_required()
    def get(self):
        """Get all groups for current user"""
        current_user_id = get_jwt_identity()

        # Get all groups where user is a member
        groups = Group.query.join(group_users).filter(
            group_users.c.user_id == current_user_id
        ).all()

        # Serialize
        result = groups_schema.dump(groups)

        return {
            'success': True,
            'groups': result
        }, 200

    @ns.doc('create_group', security='Bearer')
    @ns.expect(group_model)
    def post(self):
        """Create a new group"""
        current_user_id = get_jwt_identity()
        data = request.get_json()

        try:
            new_group = Group(
                name=data.get('name'),
                description=data.get('description', ''),
                created_by=current_user_id
            )

            db.session.add(new_group)
            db.session.flush()  # Get group ID without committing

            # Add creator as member
            current_user = User.query.get(current_user_id)
            if current_user:
                new_group.members.append(current_user)

            # Add other members if provided
            member_ids = data.get('member_ids', [])
            for member_id in member_ids:
                if member_id != current_user_id:  # Don't add creator twice
                    member = User.query.get(member_id)
                    if member:
                        new_group.members.append(member)

            db.session.commit()

            result = group_schema.dump(new_group)

            return {
                'success': True,
                'group': result,
                'message': 'Group created successfully'
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>')
@ns.param('id', 'Group ID')
class GroupDetail(Resource):
    @ns.doc('get_group', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get a specific group by ID"""
        current_user_id = get_jwt_identity()

        # Check if user is a member of this group
        group = Group.query.join(group_users).filter(
            Group.id == id,
            group_users.c.user_id == current_user_id
        ).first()

        if not group:
            return {'success': False, 'error': 'Group not found or access denied'}, 404

        result = group_schema.dump(group)

        return {
            'success': True,
            'group': result
        }, 200

    @ns.doc('update_group', security='Bearer')
    @ns.expect(group_model)
    def put(self, id):
        """Update a group"""
        current_user_id = get_jwt_identity()

        group = Group.query.filter_by(id=id).first()

        if not group:
            return {'success': False, 'error': 'Group not found'}, 404

        # Check if user is the creator or a member
        if group.created_by != current_user_id:
            is_member = db.session.query(group_users).filter(
                group_users.c.group_id == id,
                group_users.c.user_id == current_user_id
            ).first()
            if not is_member:
                return {'success': False, 'error': 'Access denied'}, 403

        data = request.get_json()

        try:
            if 'name' in data:
                group.name = data['name']
            if 'description' in data:
                group.description = data['description']

            # Update members if provided (only creator can do this)
            if 'member_ids' in data and group.created_by == current_user_id:
                # Clear existing members
                group.members.clear()

                # Add creator
                creator = User.query.get(current_user_id)
                if creator:
                    group.members.append(creator)

                # Add other members
                member_ids = data.get('member_ids', [])
                for member_id in member_ids:
                    if member_id != current_user_id:
                        member = User.query.get(member_id)
                        if member:
                            group.members.append(member)

            db.session.commit()

            result = group_schema.dump(group)

            return {
                'success': True,
                'group': result,
                'message': 'Group updated successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400

    @ns.doc('delete_group', security='Bearer')
    def delete(self, id):
        """Delete a group (only creator can delete)"""
        current_user_id = get_jwt_identity()

        group = Group.query.filter_by(id=id, created_by=current_user_id).first()

        if not group:
            return {'success': False, 'error': 'Group not found or access denied'}, 404

        try:
            db.session.delete(group)
            db.session.commit()

            return {
                'success': True,
                'message': 'Group deleted successfully'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }, 400


@ns.route('/<int:id>/members')
@ns.param('id', 'Group ID')
class GroupMembers(Resource):
    @ns.doc('get_group_members', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get all members of a group"""
        current_user_id = get_jwt_identity()

        # Check if user is a member
        group = Group.query.join(group_users).filter(
            Group.id == id,
            group_users.c.user_id == current_user_id
        ).first()

        if not group:
            return {'success': False, 'error': 'Group not found or access denied'}, 404

        # Get members
        from schemas import users_schema
        members = group.members

        result = users_schema.dump(members)

        return {
            'success': True,
            'members': result
        }, 200


@ns.route('/<int:id>/balances')
@ns.param('id', 'Group ID')
class GroupBalances(Resource):
    @ns.doc('get_group_balances', security='Bearer')
    @jwt_required()
    def get(self, id):
        """Get IOU balances within a group"""
        current_user_id = get_jwt_identity()

        # Check if user is a member
        group = Group.query.join(group_users).filter(
            Group.id == id,
            group_users.c.user_id == current_user_id
        ).first()

        if not group:
            return {'success': False, 'error': 'Group not found or access denied'}, 404

        # Calculate balances (this would need implementation in the Group model)
        # For now, return a placeholder
        balances = []

        if hasattr(group, 'calculate_balances'):
            balances = group.calculate_balances()

        return {
            'success': True,
            'group_id': id,
            'balances': balances
        }, 200
