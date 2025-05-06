import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Stripe configuration
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    
    # Review extraction settings
    MAX_FREE_URLS_PER_MONTH = 100
    MAX_FREE_REVIEWS_PER_URL = 100
    MAX_PREMIUM_URLS_PER_MONTH = 1000
    MAX_PREMIUM_REVIEWS_PER_URL = 500
    
    # Supported platforms
    SUPPORTED_PLATFORMS = ['prom', 'rozetka'] 