from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
import logging
from flask import current_app

from app.extractors.base import BaseExtractor
from app.config.prom import PROM_CONFIG

logger = logging.getLogger(__name__)

class PromExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(PROM_CONFIG)
        
    def get_product_id_from_url(self, url: str) -> str:
        """Extract product ID from Prom.ua URL."""
        pattern = r'/p(\d+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
        
    def extract_reviews(self, html: str) -> List[Dict[str, Any]]:
        """Extract reviews from product page HTML."""
        soup = BeautifulSoup(html, 'lxml')
        reviews = []
        
        logger.info("Починаємо витяг відгуків")
        
        # Знаходимо всі відгуки за стабільним data-qaid
        review_items = soup.find_all('div', attrs={'data-qaid': 'opinion_item'})
        
        logger.info(f"Знайдено відгуків: {len(review_items)}")
        
        for item in review_items:
            review = {}
            
            # Автор
            author_elem = item.find('span', attrs={'data-qaid': 'author_name'})
            review['author'] = author_elem.text.strip() if author_elem else None
            
            # Дата
            date_elem = item.find('time', attrs={'data-qaid': 'date_created'})
            review['date'] = date_elem.text.strip() if date_elem else None
            
            # Рейтинг (шукаємо по svg з data-qaid="count_stars")
            rating_elem = item.find('svg', attrs={'data-qaid': 'count_stars'})
            if rating_elem and 'data-qaid-raiting' in rating_elem.attrs:
                review['rating'] = int(rating_elem['data-qaid-raiting']) // 20  # Конвертуємо з відсотків у зірки
            else:
                review['rating'] = None
            
            # Заголовок відгуку
            title_elem = item.find('span', attrs={'data-qaid': 'title'})
            review['title'] = title_elem.text.strip() if title_elem else None
            
            # Перевірка покупки
            purchase_elem = item.find('span', attrs={'data-qaid': 'prom_label_text'})
            review['verified_purchase'] = bool(purchase_elem)
            
            # ID відгуку
            if 'data-qaopinionid' in item.attrs:
                review['platform_review_id'] = item['data-qaopinionid']
            
            reviews.append(review)
            logger.debug(f"Оброблено відгук: {review}")
            
        return reviews
        
    def extract_product_info(self, html: str) -> Dict[str, Any]:
        """Extract product information from HTML."""
        soup = BeautifulSoup(html, 'lxml')
        product_info = {}
        
        # Шукаємо заголовок товару
        title_elem = soup.find('h1', attrs={'data-qaid': 'page_title'})
        if not title_elem:
            title_elem = soup.find('h1', attrs={'data-qaid': 'product_name'})
            
        if title_elem:
            product_info['title'] = title_elem.get_text(strip=True)
            logger.info(f"Знайдено заголовок товару: {product_info['title']}")
        else:
            logger.error("Заголовок товару не знайдено")
            
        return product_info

    def find_element(self, soup, selector_config):
        """Find element using selector config that can be string or list of strings."""
        if isinstance(selector_config, list):
            # Якщо це список селекторів, пробуємо кожен по черзі
            for selector in selector_config:
                element = soup.select_one(selector)
                if element:
                    return element
            return None
        elif isinstance(selector_config, str):
            # Якщо це просто рядок, використовуємо його як селектор
            return soup.select_one(selector_config)
        elif isinstance(selector_config, dict):
            # Якщо це словник з конфігурацією
            selector = selector_config.get('selector')
            if isinstance(selector, list):
                # Якщо селектор - список, пробуємо кожен
                for sel in selector:
                    element = soup.select_one(sel)
                    if element:
                        return element
            else:
                # Якщо селектор - рядок
                return soup.select_one(selector)
        return None

    def find_elements(self, soup, selector_config):
        """Find all elements using selector config that can be string or list of strings."""
        if isinstance(selector_config, list):
            # Якщо це список селекторів, пробуємо кожен по черзі
            for selector in selector_config:
                elements = soup.select(selector)
                if elements:
                    return elements
            return []
        elif isinstance(selector_config, str):
            # Якщо це просто рядок, використовуємо його як селектор
            return soup.select(selector_config)
        elif isinstance(selector_config, dict):
            # Якщо це словник з конфігурацією
            selector = selector_config.get('selector')
            if isinstance(selector, list):
                # Якщо селектор - список, пробуємо кожен
                for sel in selector:
                    elements = soup.select(sel)
                    if elements:
                        return elements
            else:
                # Якщо селектор - рядок
                return soup.select(selector)
        return [] 