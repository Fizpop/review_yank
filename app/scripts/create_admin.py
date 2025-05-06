import os
import sys

# Додаємо корінь проєкту до PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.models.user import User

def create_admin_user():
    app = create_app()
    with app.app_context():
        # Перевіряємо чи існує адмін
        admin = User.query.filter_by(email='dasssiks@gmail.com').first()
        if not admin:
            admin = User(
                email='dasssiks@gmail.com',
                password='admin123',  # В реальному проєкті використовуйте безпечний пароль
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")

if __name__ == '__main__':
    create_admin_user() 