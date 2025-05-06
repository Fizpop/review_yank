from app import create_app, db
from app.models.platform import Platform

def add_rozetka():
    """Add Rozetka platform with configuration"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if platform already exists
            platform = Platform.query.filter_by(domain='rozetka.com.ua').first()
            if platform:
                print("Платформа Rozetka вже існує")
                return
                
            # Create platform with configuration
            config = {
                "parser": {
                    "type": "html",
                    "config": {
                        "parser": "lxml"
                    }
                },
                "selectors": {
                    "product": {
                        "title": {
                            "selector": "h1.product__title",
                            "type": "text"
                        }
                    },
                    "reviews": {
                        "container": "div.product-comments",
                        "item": "div.comment__inner",
                        "fields": {
                            "author": {
                                "selector": "span.comment__author",
                                "type": "text"
                            },
                            "date": {
                                "selector": "time.comment__date",
                                "type": "text"
                            },
                            "rating": {
                                "selector": "div.rating-stars",
                                "type": "number",
                                "attribute": "data-rating"
                            },
                            "text": {
                                "selector": "div.comment__text",
                                "type": "text"
                            },
                            "advantages": {
                                "selector": "div.comment__advantages",
                                "type": "text"
                            },
                            "disadvantages": {
                                "selector": "div.comment__disadvantages",
                                "type": "text"
                            }
                        }
                    }
                }
            }
            
            platform = Platform(
                name='Rozetka',
                domain='rozetka.com.ua',
                description='Найбільший український інтернет-магазин'
            )
            platform.set_config(config)
            
            db.session.add(platform)
            db.session.commit()
            print("Платформу Rozetka успішно додано")
            
        except Exception as e:
            print(f"Помилка при додаванні платформи: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    add_rozetka() 