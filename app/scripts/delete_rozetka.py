from app import create_app, db
from app.models.platform import Platform

def delete_rozetka():
    """Delete Rozetka platform from database"""
    app = create_app()
    
    with app.app_context():
        try:
            # Find and delete platform
            platform = Platform.query.filter_by(domain='rozetka.com.ua').first()
            if platform:
                db.session.delete(platform)
                db.session.commit()
                print("Платформу Rozetka успішно видалено")
            else:
                print("Платформу Rozetka не знайдено в базі даних")
                
        except Exception as e:
            print(f"Помилка при видаленні платформи: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    delete_rozetka() 