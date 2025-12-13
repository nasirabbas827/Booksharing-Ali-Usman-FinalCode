"""
Database Models for Book Sharing Platform

Defines all SQLAlchemy models and enums used in the Flask application:
- User (with authentication support via Flask-Login)
- Category (for organizing books)
- Book (physical or digital, with ownership and availability status)
- BorrowRequest (handles borrowing workflow between users)
- Message (chat between borrower and owner for a specific request)
- Admin (separate admin user with plain text password for simplicity)
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import enum

# Global SQLAlchemy instance (initialized in the main app)
db = SQLAlchemy()


# ========================
# Enums
# ========================

class UserStatus(enum.Enum):
    """Status of a user account."""
    blocked = "blocked"
    unblocked = "unblocked"


class BorrowStatus(enum.Enum):
    """Possible states of a borrow request."""
    pending = "pending"      # Initial state - waiting for owner response
    accepted = "accepted"    # Owner accepted the request
    rejected = "rejected"    # Owner rejected the request
    modified = "modified"    # Owner proposed different date/time/location
    returned = "returned"    # Book has been returned (completed)


# ========================
# User Model
# ========================
class User(UserMixin, db.Model):
    """Represents a registered user of the platform."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    profile_picture = db.Column(db.String(200))  # Relative path
    
    status = db.Column(
        db.Enum(UserStatus),
        default=UserStatus.unblocked,
        nullable=False
    )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.unblocked

    @property
    def is_admin(self):
        return False

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"


# ========================
# Category Model
# ========================
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


# ========================
# Book Model
# ========================
class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), index=True)
    
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    book_image = db.Column(db.String(255))
    
    book_type = db.Column(db.String(20), nullable=False)  # 'physical' or 'digital'
    status = db.Column(
        db.Enum('available', 'unavailable', name='book_status'),
        default='available',
        nullable=False
    )
    
    physical_location = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    download_link = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    category = db.relationship('Category', backref='books', lazy=True)
    owner = db.relationship('User', backref='books', lazy=True)

    def __repr__(self) -> str:
        return f"<Book '{self.title}' by {self.author} ({self.book_type})>"


# ========================
# BorrowRequest Model (FIXED: Now uses strings for date/time)
# ========================
class BorrowRequest(db.Model):
    """Tracks a borrow request from a borrower to a book owner."""
    __tablename__ = 'borrow_requests'

    id = db.Column(db.Integer, primary_key=True)
    
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Borrower-proposed details — stored as strings (YYYY-MM-DD and HH:MM)
    proposed_date = db.Column(db.String(20), nullable=False)      # e.g., "2025-12-14"
    proposed_time = db.Column(db.String(10), nullable=False)      # e.g., "14:30"
    proposed_location = db.Column(db.String(255), nullable=False)
    
    # Owner counter-proposal (optional)
    owner_proposed_date = db.Column(db.String(20), nullable=True)
    owner_proposed_time = db.Column(db.String(10), nullable=True)
    
    # Request status
    status = db.Column(
        db.Enum(BorrowStatus),
        default=BorrowStatus.pending,
        nullable=False
    )
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    book = db.relationship('Book', backref='borrow_requests', lazy=True)
    borrower = db.relationship('User', foreign_keys=[borrower_id], backref='outgoing_requests', lazy=True)
    owner = db.relationship('User', foreign_keys=[owner_id], backref='incoming_requests', lazy=True)

    def __repr__(self) -> str:
        return f"<BorrowRequest #{self.id} | Book:{self.book_id} | Status:{self.status.value}>"


# ========================
# Message Model
# ========================
class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    borrow_request_id = db.Column(db.Integer, db.ForeignKey('borrow_requests.id'), nullable=False)
    
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages', lazy=True)
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages', lazy=True)
    borrow_request = db.relationship('BorrowRequest', backref='messages', lazy=True)

    def __repr__(self) -> str:
        return f"<Message #{self.id} | From:{self.sender_id} To:{self.receiver_id}>"


# ========================
# Admin Model (Plain Text Password - Safe & Fixed)
# ========================
class Admin(UserMixin, db.Model):
    """Separate admin user model with a FIXED ID to prevent collisions."""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True, autoincrement=False)  # Fixed manual ID
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)  # Plain text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_admin(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @staticmethod
    def create_default_admin():
        if Admin.query.filter_by(username='admin').first():
            return

        admin = Admin(
            id=999999,
            username='admin',
            password='admin'
        )
        db.session.add(admin)
        db.session.commit()

        from flask import current_app
        current_app.logger.info("Default admin created: username='admin', password='admin' (ID: 999999)")
        current_app.logger.warning("SECURITY TIP: Change the default admin password after first login!")

    def __repr__(self):
        return f"<Admin {self.username} (ID: {self.id})>"