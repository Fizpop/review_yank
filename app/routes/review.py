from flask import Blueprint, render_template, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from app.models.extraction import Extraction, Review
from app.services.extractor import ReviewExtractor, extract_page_content
from app.services.ai_helper import AIHelper
from app import db
from datetime import datetime
import re
import json
import requests

bp = Blueprint('review', __name__)

def parse_ukrainian_date(date_str):
    """Конвертує українську дату в об'єкт datetime"""
    if not date_str:
        return None
        
    # Словник для конвертації українських назв місяців
    month_map = {
        'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
        'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
        'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
    }
    
    try:
        # Розбиваємо рядок на день, місяць та рік
        match = re.match(r'(\d+)\s+(\w+)\s+(\d+)', date_str)
        if match:
            day, month_name, year = match.groups()
            month = month_map.get(month_name.lower())
            if month:
                return datetime(int(year), month, int(day))
    except (ValueError, AttributeError):
        pass
        
    return None

@bp.route('/extract', methods=['POST'])
@login_required
def extract():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL не вказано'}), 400
            
        # Створюємо новий запис про витяг
        extraction = Extraction(
            url=url,
            status='processing',
            created_at=datetime.utcnow(),
            user_id=current_user.id,
            platform='unknown'
        )
        db.session.add(extraction)
        db.session.commit()
        
        try:
            # Отримуємо HTML сторінки використовуючи той самий метод, що і в тестуванні
            html_content = extract_page_content(url)
            if not html_content:
                extraction.status = 'error'
                extraction.error_message = 'Не вдалося отримати вміст сторінки'
                db.session.commit()
                return jsonify({'error': 'Не вдалося отримати вміст сторінки'}), 400
            
            # Використовуємо екстрактор
            extractor = ReviewExtractor()
            result = extractor.extract_reviews(html_content, url)
            
            if not result:
                extraction.status = 'error'
                extraction.error_message = 'Не вдалося витягти відгуки'
                db.session.commit()
                return jsonify({'error': 'Не вдалося витягти відгуки'}), 400
                
            if not isinstance(result, dict) or 'reviews' not in result:
                extraction.status = 'error'
                extraction.error_message = 'Неправильний формат результату витягу'
                db.session.commit()
                return jsonify({'error': 'Неправильний формат результату витягу'}), 400
            
            # Зберігаємо результати
            for review_data in result['reviews']:
                review = Review(
                    extraction_id=extraction.id,
                    author=review_data.get('author'),
                    text=review_data.get('text') or review_data.get('title'),  # Використовуємо title якщо text відсутній
                    rating=review_data.get('rating'),
                    date=review_data.get('date'),
                    advantages=review_data.get('advantages'),
                    disadvantages=review_data.get('disadvantages'),
                    platform_review_id=review_data.get('platform_review_id')
                )
                db.session.add(review)
            
            extraction.status = 'completed'
            extraction.title = result.get('product_title', '')
            extraction.platform = result.get('platform', 'unknown')
            extraction.completed_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'extraction_id': extraction.id,
                'reviews_count': len(result['reviews'])
            })
            
        except Exception as e:
            extraction.status = 'error'
            extraction.error_message = f'Помилка обробки: {str(e)}'
            db.session.commit()
            current_app.logger.error(f"Error processing extraction: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in extract_reviews: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/extractions')
@login_required
def list_extractions():
    extractions = current_user.extractions.order_by(Extraction.created_at.desc()).all()
    return render_template('review/extractions.html', extractions=extractions)

@bp.route('/extraction/<int:id>')
@login_required
def view_extraction(id):
    extraction = Extraction.query.get_or_404(id)
    if extraction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    reviews = [review.to_dict() for review in extraction.reviews]
    return render_template('review/extraction.html', extraction=extraction, reviews=reviews)

@bp.route('/api/extraction/<int:id>/export')
@login_required
def export_extraction(id):
    extraction = Extraction.query.get_or_404(id)
    if extraction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    format = request.args.get('format', 'json')
    reviews = [review.to_dict() for review in extraction.reviews]
    
    if format == 'json':
        return jsonify(reviews)
    elif format == 'csv':
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=reviews[0].keys())
        writer.writeheader()
        writer.writerows(reviews)
        
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=reviews_{extraction.id}.csv'
        }
    else:
        return jsonify({'error': 'Unsupported format'}), 400

@bp.route('/extraction/<int:extraction_id>/summary')
@login_required
def get_summary(extraction_id):
    try:
        extraction = Extraction.query.get_or_404(extraction_id)
        
        # Перевіряємо чи користувач має доступ до цього extraction
        if extraction.user_id != current_user.id:
            abort(403)
        
        # Отримуємо всі відгуки
        reviews = Review.query.filter_by(extraction_id=extraction_id).all()
        
        if not reviews:
            return jsonify({'error': 'Відгуки не знайдено'}), 404
        
        # Підготовка даних для ШІ
        reviews_text = "\n\n".join([
            f"Відгук від {review.author}:\n"
            f"Рейтинг: {review.rating}\n"
            f"Текст: {review.text}"
            for review in reviews
        ])
        
        # Створюємо промт для ШІ
        prompt = f"""Проаналізуй наступні відгуки про товар "{extraction.title}" та надай:
1. Загальний підсумок у 2-3 реченнях
2. Список основних переваг (максимум 5)
3. Список основних недоліків (максимум 5)

Відгуки:
{reviews_text}

Поверни результат у форматі JSON:
{{
    "summary": "загальний підсумок",
    "pros": ["перевага 1", "перевага 2", ...],
    "cons": ["недолік 1", "недолік 2", ...]
}}"""

        # Використовуємо той самий ШІ сервіс для аналізу
        ai_helper = AIHelper()
        response = ai_helper._make_request_with_retry(prompt)
        
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Якщо відповідь не в JSON форматі, шукаємо JSON в тексті
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
                return jsonify({'error': 'Неправильний формат відповіді від ШІ'}), 500
        
        # Додаємо середній рейтинг
        average_rating = sum(review.rating for review in reviews) / len(reviews)
        result['average_rating'] = average_rating
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in get_summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/extraction/<int:id>/delete', methods=['POST'])
@login_required
def delete_extraction(id):
    extraction = Extraction.query.get_or_404(id)
    
    # Перевіряємо чи користувач має доступ до цього extraction
    if extraction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Видаляємо всі пов'язані відгуки
        Review.query.filter_by(extraction_id=id).delete()
        
        # Видаляємо сам витяг
        db.session.delete(extraction)
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 