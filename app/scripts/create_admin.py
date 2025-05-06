from app import create_app, db
from app.models.user import User

def create_admin():
    """Create a new admin user"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if admin already exists
            admin = User.query.filter_by(email='admin@example.com').first()
            if admin:
                print("Адміністратор вже існує")
                return
                
            # Create new admin user
            admin = User(
                email='admin@example.com',
                username='admin',
                is_admin=True
            )
            admin.set_password('admin')
            
            db.session.add(admin)
            db.session.commit()
            print("Адміністратор успішно створений")
            
        except Exception as e:
            print(f"Помилка при створенні адміністратора: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    create_admin() 