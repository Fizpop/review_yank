from flask import Flask, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
login = LoginManager()
migrate = Migrate()
login.login_view = 'auth.login'

@login.unauthorized_handler
def unauthorized_callback():
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = jsonify({'error': 'login_required'})
        response.status_code = 401
        if 'WWW-Authenticate' in response.headers:
            del response.headers['WWW-Authenticate']
        return response
    return redirect(url_for('auth.login', next=request.url))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login.init_app(app)
    migrate.init_app(app, db)
    
    from app.routes import main, auth, review, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(review.bp)
    app.register_blueprint(admin.bp)
    
    return app 