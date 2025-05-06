from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

def create_user():
    """Create a new user with admin privileges"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if user already exists
            user = User.query.filter_by(email='dasssiks@gmail.com').first()
            if user:
                print("Користувач вже існує")
                return
                
            # Create new user
            user = User(
                username='dasssiks',
                email='dasssiks@gmail.com',
                password_hash=generate_password_hash('123123q'),
                is_admin=True
            )
            
            db.session.add(user)
            db.session.commit()
            print("Користувача успішно створено")
            
        except Exception as e:
            print(f"Помилка при створенні користувача: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    create_user() 