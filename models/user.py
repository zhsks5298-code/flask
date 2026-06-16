from datetime import datetime
from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(50))
    email = db.Column(db.String(100))
    role = db.Column(db.Enum('viewer','operator','maintainer','admin'), default='viewer')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)
    password_changed_at = db.Column(db.DateTime)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    def is_locked(self):
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def has_role(self, required_role):
        hierarchy = ['viewer', 'operator', 'maintainer', 'admin']
        try:
            return hierarchy.index(self.role) >= hierarchy.index(required_role)
        except ValueError:
            return False
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class LoginHistory(db.Model):
    __tablename__ = 'login_history'
    
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer)
    event_type = db.Column(db.Enum('login_success','login_fail','logout','session_timeout'), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    fail_reason = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)