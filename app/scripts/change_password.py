from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

def change_password(username, new_password):
    """Change password for a user"""
    app = create_app()
    
    with app.app_context():
        try:
            user = User.query.filter_by(username=username).first()
            if not user:
                print(f"Користувача {username} не знайдено")
                return
                
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            print(f"Пароль для користувача {username} успішно змінено")
            
        except Exception as e:
            print(f"Помилка при зміні пароля: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    change_password("dasssiks@gmail.com", "123123q") 