from datetime import datetime
from app import db

class Extraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    title = db.Column(db.String(500))  # Назва товару
    error_message = db.Column(db.Text)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    reviews = db.relationship('Review', backref='extraction', lazy='dynamic')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(100))
    text = db.Column(db.Text)
    rating = db.Column(db.Float)
    date = db.Column(db.String(100))  # Змінюємо тип на String
    advantages = db.Column(db.Text)  # Додаємо поле для переваг
    disadvantages = db.Column(db.Text)  # Додаємо поле для недоліків
    platform_review_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    extraction_id = db.Column(db.Integer, db.ForeignKey('extraction.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'author': self.author,
            'text': self.text,
            'rating': self.rating,
            'date': self.date,
            'advantages': self.advantages,
            'disadvantages': self.disadvantages,
            'platform_review_id': self.platform_review_id,
            'created_at': self.created_at.isoformat(),
            'product_title': self.extraction.title
        } 