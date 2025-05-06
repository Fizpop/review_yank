from app import db
from datetime import datetime
import json

class Platform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    config = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Platform {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'domain': self.domain,
            'description': self.description,
            'config': json.loads(self.config) if self.config else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def set_config(self, config):
        """Set platform configuration"""
        if isinstance(config, dict):
            self.config = json.dumps(config)
        else:
            self.config = config

    @staticmethod
    def get_default_config():
        return {
            'rozetka': {
                'name': 'Rozetka',
                'domain': 'rozetka.com.ua',
                'selectors': {
                    'product_title': 'h1.product__title',
                    'reviews_container': 'ul.product-comments__list',
                    'review_item': '.product-comments__list-item',
                    'review_fields': {
                        'author': "[data-testid='replay-header-author']",
                        'text': ".comment__body-wrapper p",
                        'rating': ".stars__rating",
                        'date': "[data-testid='replay-header-date']",
                        'advantages': ".comment__essentials dd",
                        'disadvantages': ".comment__essentials dd:nth-of-type(2)",
                        'product_info': ".comment__vars"
                    },
                    'pagination': {
                        'next_page': 'a.pagination__direction_type_forward',
                        'page_param': 'page'
                    }
                }
            },
            'prom': {
                'name': 'Prom.ua',
                'domain': 'prom.ua',
                'selectors': {
                    'product_title': 'h1[data-qaid="page_title"]',
                    'reviews_container': 'div[data-qaid="comments_list"]',
                    'review_item': 'div[data-qaid="opinion_item"]',
                    'review_fields': {
                        'author': 'div[data-qaid="opinion_author"]',
                        'text': 'div[data-qaid="opinion_text"]',
                        'rating': 'div[data-qaid="opinion_rating"]',
                        'date': 'time[data-qaid="opinion_date"]',
                        'advantages': 'div[data-qaid="opinion_pros"]',
                        'disadvantages': 'div[data-qaid="opinion_cons"]'
                    },
                    'pagination': {
                        'next_page': 'a[data-qaid="pagination_next"]',
                        'page_param': 'page'
                    }
                }
            }
        } 