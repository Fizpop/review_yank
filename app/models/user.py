from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_premium = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    extractions = db.relationship('Extraction', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
        
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_max_urls_per_month(self):
        return 100 if self.is_premium else 5
        
    def get_max_reviews_per_url(self):
        return 500 if self.is_premium else 100
        
    def get_remaining_urls(self):
        from app.models.extraction import Extraction
        used = self.extractions.filter(
            Extraction.created_at >= datetime.utcnow().replace(day=1)
        ).count()
        return self.get_max_urls_per_month() - used 