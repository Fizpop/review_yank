from app import create_app, db

def init_db():
    """Initialize the database and create all tables"""
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("База даних успішно створена")
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")

if __name__ == "__main__":
    init_db() 