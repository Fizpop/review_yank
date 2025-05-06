from app import create_app, db
from app.models.platform import Platform

def init_platforms():
    """Initialize platforms"""
    app = create_app()
    
    with app.app_context():
        try:
            # Add Prom platform
            prom = Platform.query.filter_by(domain='prom.ua').first()
            if not prom:
                prom = Platform(
                    name='Prom.ua',
                    domain='prom.ua',
                    description='Маркетплейс Prom.ua'
                )
                db.session.add(prom)
            
            # Add Rozetka platform
            rozetka = Platform.query.filter_by(domain='rozetka.com.ua').first()
            if not rozetka:
            rozetka = Platform(
                name='Rozetka',
                domain='rozetka.com.ua',
                    description='Інтернет-магазин Rozetka'
            )
            db.session.add(rozetka)
            
            db.session.commit()
            print("Платформи успішно додані")
            
        except Exception as e:
            print(f"Помилка при додаванні платформ: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    init_platforms() 