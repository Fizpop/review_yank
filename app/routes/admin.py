from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app import db
from app.models.platform import Platform
from app.models.user import User
from app.services.extractor import ReviewExtractor, extract_page_content
from app.services.ai_helper import AIHelper
from app.utils.auth import admin_required
import json

bp = Blueprint('admin', __name__, url_prefix='/admin')
ai_helper = AIHelper()

@bp.before_request
@login_required
def check_admin():
    if not current_user.is_admin:
        flash('Доступ заборонено. Необхідні права адміністратора.', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/platforms')
def platforms():
    platforms = Platform.query.all()
    return render_template('admin/platforms.html', platforms=platforms)

@bp.route('/platforms/<int:id>', methods=['GET'])
def get_platform(id):
    platform = Platform.query.get_or_404(id)
    return jsonify(platform.to_dict())

@bp.route('/platforms/default-config')
def get_default_config():
    return jsonify(Platform.get_default_config())

@bp.route('/platform', methods=['POST'])
@login_required
def add_platform_new():
    try:
        data = request.get_json()
        name = data.get('name')
        domain = data.get('domain')
        config = data.get('config')
        description = data.get('description')
        
        if not all([name, domain, config]):
            return jsonify({'error': 'Не всі поля заповнені'}), 400
            
        # Переконуємось що config це рядок JSON
        if isinstance(config, dict):
            config = json.dumps(config)
            
        platform = Platform(
            name=name,
            domain=domain,
            description=description,
            config=config
        )
        
        db.session.add(platform)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Платформу додано'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding platform: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/platforms/<int:id>', methods=['PUT'])
def update_platform(id):
    try:
        platform = Platform.query.get_or_404(id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Не вдалося отримати дані'}), 400
            
        platform.name = data.get('name', platform.name)
        platform.domain = data.get('domain', platform.domain)
        
        # Переконуємось що config це рядок JSON
        if 'config' in data:
            config = data['config']
            if isinstance(config, dict):
                config = json.dumps(config)
            platform.config = config
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Платформу оновлено'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@bp.route('/platforms/<int:id>', methods=['DELETE'])
@login_required
def delete_platform(id):
    try:
        platform = Platform.query.get_or_404(id)
        db.session.delete(platform)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Платформу видалено'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting platform: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/platforms/<int:id>/test', methods=['POST'])
@login_required
def test_platform(id):
    """Тестування платформи з витяганням відгуків"""
    try:
        platform = Platform.query.get_or_404(id)
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL не вказано'})
            
        extractor = ReviewExtractor()
        
        # Отримуємо HTML-код сторінки
        html_content = extract_page_content(url)
        if not html_content:
            return jsonify({'success': False, 'error': 'Не вдалося отримати контент сторінки'})
            
        # Логуємо частину HTML для дебагу
        current_app.logger.info(f"HTML content preview: {html_content[:1000]}")
            
        # Витягуємо відгуки
        result = extractor.extract_reviews(html_content, url)
        if not result:
            return jsonify({'success': False, 'error': 'Не вдалося витягти відгуки'})
            
        reviews = result.get('reviews', [])
        
        # Підготуємо детальну інформацію про перші 3 відгуки
        sample_reviews = []
        for review in reviews[:3]:
            sample_review = {
                'author': review.get('author', 'Невідомо'),
                'date': review.get('date'),
                'rating': review.get('rating', 0),
                'text': review.get('text', ''),
                'advantages': review.get('advantages', ''),
                'disadvantages': review.get('disadvantages', ''),
                'verified_purchase': review.get('verified_purchase', False),
                'platform_review_id': review.get('platform_review_id', '')
            }
            sample_reviews.append(sample_review)
        
        return jsonify({
            'success': True,
            'reviews_count': len(reviews),
            'sample_reviews': sample_reviews
        })
        
    except Exception as e:
        current_app.logger.error(f"Помилка при тестуванні платформи: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/platforms/generate-config', methods=['POST'])
@login_required
def generate_platform_config():
    try:
        data = request.get_json()
        url = data.get('url')
        title_block = data.get('title_block')
        review_block = data.get('review_block')

        if not url or not title_block or not review_block:
            return jsonify({
                'success': False,
                'error': 'Не вказано URL або блоки HTML'
            })

        ai_helper = AIHelper()
        config = ai_helper.generate_platform_config_from_examples(
            url=url,
            title_example=title_block,
            review_example=review_block
        )

        if not config:
            return jsonify({
                'success': False,
                'error': 'Не вдалося згенерувати конфігурацію'
            })

        return jsonify({
            'success': True,
            'config': config
        })

    except Exception as e:
        current_app.logger.error(f"Помилка при генерації конфігурації: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/platforms/test-config', methods=['POST'])
@login_required
def test_config():
    """Тестування конфігурації з HTML блоків"""
    try:
        data = request.get_json()
        url = data.get('url')
        title_block = data.get('title-block')
        review_block = data.get('review-block')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL не вказано'})
            
        if not title_block and not review_block:
            return jsonify({'success': False, 'error': 'Потрібно надати хоча б один HTML блок'})
            
        # Отримуємо HTML сторінки
        html_content = extract_page_content(url)
        if not html_content:
            return jsonify({'success': False, 'error': 'Не вдалося отримати контент сторінки'})
            
        # Генеруємо конфігурацію
        config = ai_helper.generate_platform_config_from_examples(
            url=url,
            title_example=title_block,
            review_example=review_block
        )
        
        if not config:
            return jsonify({'success': False, 'error': 'Не вдалося згенерувати конфігурацію'})
            
        # Тестуємо згенеровану конфігурацію
        extractor = ReviewExtractor()
        result = extractor.extract_reviews(html_content, url)
        
        if not result or not result.get('reviews'):
            return jsonify({'success': False, 'error': 'Не вдалося витягти відгуки з тестової конфігурації'})
            
        return jsonify({
            'success': True,
            'config': config,
            'test_results': {
                'reviews_count': len(result['reviews']),
                'sample_review': result['reviews'][0] if result['reviews'] else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Помилка при тестуванні конфігурації: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }) 