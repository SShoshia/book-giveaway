from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    interests = db.relationship('Book', secondary='user_book_interest', back_populates='interested_users')

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    owner_id = db.Column(db.String(50), db.ForeignKey('user.id'), nullable=False)
    
    owner = db.relationship('User')

    interested_users = db.relationship('User', secondary='user_book_interest', back_populates='interests')

class UserBookInterest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
