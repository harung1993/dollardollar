"""
Group Service
Business logic for group management and bill splitting
"""

import json
from flask import current_app
from src.extensions import db
from src.models.group import Group, Settlement
from src.models.user import User
from src.models.transaction import Expense
from src.models.associations import group_users
from src.utils.helpers import calculate_balances


class GroupService:
    """Service class for group operations"""

    def __init__(self):
        pass

    # Group CRUD Methods

    def get_all_groups(self, user_id):
        """Get all groups where user is a member"""
        return Group.query.join(group_users).filter(group_users.c.user_id == user_id).all()

    def get_group(self, group_id, user_id):
        """
        Get a specific group with member validation
        Returns (success, message, group)
        """
        group = Group.query.get(group_id)
        if not group:
            return False, 'Group not found', None

        # Check if user is member
        user = User.query.get(user_id)
        if user not in group.members:
            return False, 'Access denied. You are not a member of this group.', None

        return True, 'Success', group

    def create_group(self, user_id, name, description, member_ids, default_split_method='equal',
                    default_payer=None, auto_include_all=False, default_split_values=None):
        """
        Create a new group
        Returns (success, message, group)
        """
        try:
            # Create group
            group = Group(
                name=name,
                description=description,
                created_by=user_id,
                default_split_method=default_split_method,
                default_payer=default_payer,
                auto_include_all=auto_include_all
            )

            # Add creator as a member
            creator = User.query.get(user_id)
            group.members.append(creator)

            # Add selected members
            for member_id in member_ids:
                user = User.query.filter_by(id=member_id).first()
                if user and user.id != user_id:
                    group.members.append(user)

            # Handle custom split values
            if default_split_method != 'equal' and default_split_values:
                if isinstance(default_split_values, str):
                    try:
                        split_values = json.loads(default_split_values)
                        group.default_split_values = split_values
                    except:
                        pass
                else:
                    group.default_split_values = default_split_values

            db.session.add(group)
            db.session.commit()

            return True, 'Group created successfully!', group

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating group: {str(e)}")
            return False, f'Error creating group: {str(e)}', None

    def add_member(self, group_id, user_id, new_member_id):
        """
        Add a member to a group
        Returns (success, message)
        """
        group = Group.query.get(group_id)
        if not group:
            return False, 'Group not found'

        # Check if current user is creator
        if group.created_by != user_id:
            return False, 'Only the group creator can add members'

        # Get new member
        new_member = User.query.filter_by(id=new_member_id).first()
        if not new_member:
            return False, 'User not found'

        # Check if already a member
        if new_member in group.members:
            return False, 'User is already a member of this group'

        try:
            group.members.append(new_member)
            db.session.commit()
            return True, f'{new_member.name} added to group successfully!'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding member: {str(e)}")
            return False, f'Error adding member: {str(e)}'

    def remove_member(self, group_id, user_id, member_id):
        """
        Remove a member from a group
        Returns (success, message)
        """
        group = Group.query.get(group_id)
        if not group:
            return False, 'Group not found'

        # Check if current user is creator
        if group.created_by != user_id:
            return False, 'Only the group creator can remove members'

        # Can't remove creator
        if member_id == group.created_by:
            return False, 'Cannot remove the group creator'

        member = User.query.filter_by(id=member_id).first()
        if not member or member not in group.members:
            return False, 'Member not found in group'

        try:
            group.members.remove(member)
            db.session.commit()
            return True, f'{member.name} removed from group successfully!'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error removing member: {str(e)}")
            return False, f'Error removing member: {str(e)}'

    def delete_group(self, group_id, user_id):
        """
        Delete a group
        Returns (success, message)
        """
        group = Group.query.get(group_id)
        if not group:
            return False, 'Group not found'

        # Only creator can delete
        if group.created_by != user_id:
            return False, 'Only the group creator can delete the group'

        try:
            # Delete associated settlements
            Settlement.query.filter_by(group_id=group_id).delete()

            # Update expenses to remove group reference
            Expense.query.filter_by(group_id=group_id).update({'group_id': None})

            # Delete the group
            db.session.delete(group)
            db.session.commit()

            return True, 'Group deleted successfully!'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting group: {str(e)}")
            return False, f'Error deleting group: {str(e)}'

    def update_settings(self, group_id, user_id, default_split_method=None, default_payer=None,
                       auto_include_all=None, default_split_values=None):
        """
        Update group settings
        Returns (success, message)
        """
        group = Group.query.get(group_id)
        if not group:
            return False, 'Group not found'

        # Only creator can update settings
        if group.created_by != user_id:
            return False, 'Only the group creator can update settings'

        try:
            if default_split_method is not None:
                group.default_split_method = default_split_method
            if default_payer is not None:
                group.default_payer = default_payer if default_payer else None
            if auto_include_all is not None:
                group.auto_include_all = auto_include_all
            if default_split_values is not None:
                if isinstance(default_split_values, str):
                    try:
                        group.default_split_values = json.loads(default_split_values)
                    except:
                        pass
                else:
                    group.default_split_values = default_split_values

            db.session.commit()
            return True, 'Group settings updated successfully!'

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating group settings: {str(e)}")
            return False, f'Error updating settings: {str(e)}'

    def get_group_expenses(self, group_id):
        """Get all expenses for a group"""
        return Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc()).all()

    def calculate_group_balances(self, group_id):
        """Calculate balances between group members"""
        expenses = self.get_group_expenses(group_id)
        group = Group.query.get(group_id)

        if not group:
            return {}

        member_ids = [member.id for member in group.members]
        return calculate_balances(expenses, member_ids)


class SettlementService:
    """Service class for settlement operations"""

    def __init__(self):
        pass

    def get_all_settlements(self, user_id):
        """Get all settlements involving the user"""
        from sqlalchemy import or_
        return Settlement.query.filter(
            or_(Settlement.payer_id == user_id, Settlement.receiver_id == user_id)
        ).order_by(Settlement.date.desc()).all()

    def add_settlement(self, payer_id, receiver_id, amount, group_id=None, description=None):
        """
        Add a settlement payment
        Returns (success, message, settlement)
        """
        try:
            settlement = Settlement(
                payer_id=payer_id,
                receiver_id=receiver_id,
                amount=float(amount),
                group_id=group_id,
                description=description
            )

            db.session.add(settlement)
            db.session.commit()

            return True, 'Settlement recorded successfully!', settlement

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding settlement: {str(e)}")
            return False, f'Error recording settlement: {str(e)}', None
