"""
Category and CategoryMapping models
"""

from datetime import datetime
from src.extensions import db

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50), default="fa-tag")  # FontAwesome icon name
    color = db.Column(db.String(20), default="#6c757d")
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    is_system = db.Column(db.Boolean, default=False)  # System categories can't be deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('categories', lazy=True))
    parent = db.relationship('Category', remote_side=[id], backref=db.backref('subcategories', lazy=True))

    def __repr__(self):
        return f"<Category: {self.name}>"


class CategoryMapping(db.Model):
    __tablename__ = 'category_mappings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    keyword = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    is_regex = db.Column(db.Boolean, default=False)  # Whether the keyword is a regex pattern
    priority = db.Column(db.Integer, default=0)  # Higher priority mappings take precedence
    match_count = db.Column(db.Integer, default=0)  # How many times this mapping has been used
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('category_mappings', lazy=True))
    category = db.relationship('Category', backref=db.backref('mappings', lazy=True))
    
    def __repr__(self):
        return f"<CategoryMapping: '{self.keyword}' → {self.category.name}>"


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(20), default="#6c757d")  # Default color gray
    user_id = db.Column(db.String(120), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('tags', lazy=True))
