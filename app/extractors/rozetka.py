from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
import logging
from flask import current_app

from app.extractors.base import BaseExtractor
from app.config.rozetka import ROZETKA_CONFIG

logger = logging.getLogger(__name__)

class RozetkaExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(ROZETKA_CONFIG)
        
    def get_product_id_from_url(self, url: str) -> str:
        """Extract product ID from Rozetka URL."""
        pattern = r'/(\d+)/'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
        
    def extract_reviews(self, html: str) -> List[Dict[str, Any]]:
        """Extract reviews from product page HTML."""
        soup = BeautifulSoup(html, 'lxml')
        reviews = []
        
        logger.info("Починаємо витяг відгуків")
        
        # Шукаємо контейнер з відгуками
        container = soup.select_one(self.config['selectors']['reviews']['container'])
        if not container:
            logger.error("Контейнер з відгуками не знайдено")
            return reviews
            
        # Шукаємо всі відгуки
        review_items = container.select(self.config['selectors']['reviews']['item'])
        logger.debug(f"Знайдено відгуків: {len(review_items)}")
        
        if not review_items:
            logger.error("Відгуки не знайдено")
            return reviews
            
        for item in review_items:
            try:
                review = {}
                
                # Виводимо HTML відгуку для діагностики
                logger.debug(f"HTML відгуку: {str(item)}")
                
                # Знаходимо автора
                author_elem = item.select_one(self.config['selectors']['reviews']['fields']['author']['selector'])
                if author_elem:
                    review['author'] = author_elem.get_text(strip=True)
                    logger.debug(f"Знайдено автора: {review['author']}")
                else:
                    logger.debug(f"Автора не знайдено")
                
                # Знаходимо дату
                date_elem = item.select_one(self.config['selectors']['reviews']['fields']['date']['selector'])
                if date_elem:
                    review['date'] = date_elem.get_text(strip=True)
                    logger.debug(f"Знайдено дату: {review['date']}")
                else:
                    logger.debug(f"Дату не знайдено")
                
                # Знаходимо рейтинг
                rating_elem = item.select_one(self.config['selectors']['reviews']['fields']['rating']['selector'])
                if rating_elem and rating_elem.has_attr(self.config['selectors']['reviews']['fields']['rating']['attribute']):
                    try:
                        rating_value = float(rating_elem[self.config['selectors']['reviews']['fields']['rating']['attribute']])
                        review['rating'] = rating_value
                        logger.debug(f"Знайдено рейтинг: {review['rating']}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Помилка конвертації рейтингу: {e}")
                        review['rating'] = 0
                else:
                    logger.debug(f"Рейтинг не знайдено")
                
                # Знаходимо текст
                text_elem = item.select_one(self.config['selectors']['reviews']['fields']['text']['selector'])
                if text_elem:
                    review['text'] = text_elem.get_text(strip=True)
                    logger.debug(f"Знайдено текст: {review['text']}")
                else:
                    logger.debug(f"Текст не знайдено")
                
                # Знаходимо переваги
                advantages_elem = item.select_one(self.config['selectors']['reviews']['fields']['advantages']['selector'])
                if advantages_elem:
                    review['advantages'] = advantages_elem.get_text(strip=True)
                    logger.debug(f"Знайдено переваги: {review['advantages']}")
                else:
                    logger.debug(f"Переваги не знайдено")
                
                # Знаходимо недоліки
                disadvantages_elem = item.select_one(self.config['selectors']['reviews']['fields']['disadvantages']['selector'])
                if disadvantages_elem:
                    review['disadvantages'] = disadvantages_elem.get_text(strip=True)
                    logger.debug(f"Знайдено недоліки: {review['disadvantages']}")
                else:
                    logger.debug(f"Недоліки не знайдено")
                
                # Додаємо ID відгуку
                review['platform_review_id'] = item.get('data-review-id', '')
                
                # Логуємо знайдені значення
                logger.debug(f"Зібрані дані відгуку: {review}")
                
                # Додаємо відгук тільки якщо є хоча б автор або текст
                if review.get('author') or review.get('text'):
                    reviews.append(review)
                    logger.debug(f"Додано відгук: {review}")
                else:
                    logger.warning("Відгук пропущено - немає автора або тексту")
                    
            except Exception as e:
                logger.error(f"Помилка при обробці відгуку: {str(e)}")
                continue
                
        logger.info(f"Загалом оброблено відгуків: {len(reviews)}")
        return reviews
        
    def extract_product_info(self, html: str) -> Dict[str, Any]:
        """Extract product information from HTML."""
        soup = BeautifulSoup(html, 'lxml')
        product_info = {}
        
        # Шукаємо заголовок товару
        title_elem = soup.select_one(self.config['selectors']['product']['title']['selector'])
        if title_elem:
            product_info['title'] = title_elem.get_text(strip=True)
            logger.info(f"Знайдено заголовок товару: {product_info['title']}")
        else:
            logger.error("Заголовок товару не знайдено")
            
        return product_info 