from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.extraction import Extraction

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', Extraction=Extraction)

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@bp.route('/premium')
@login_required
def premium():
    return render_template('premium.html') 