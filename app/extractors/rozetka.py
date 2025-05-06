from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re
import logging
from flask import current_app
from playwright.sync_api import sync_playwright
import time
import os

from app.extractors.base import BaseExtractor
from app.config.rozetka import ROZETKA_CONFIG

logger = logging.getLogger(__name__)

def extract_rating(rating_element):
    if not rating_element:
        return None
    if 'style' in rating_element.attrs:
        style = rating_element['style']
        pattern = r'width:\s*calc\((\d+)%\s*-\s*2px\)'
        m = re.search(pattern, style)
        if m:
            width = int(m.group(1))
            return width // 20
    return None

def extract_review_data(review):
    data = {
        'rating': None,
        'author': None,
        'date': None,
        'text': None,
        'advantages': None,
        'disadvantages': None,
        'likes': 0,
        'dislikes': 0,
        'bought': False,
        'comment_photos': [],
    }
    # Рейтинг
    rating_element = review.select_one('[data-testid="stars-rating"]')
    data['rating'] = extract_rating(rating_element)
    # Автор
    author_element = review.select_one('[data-testid="replay-header-author"]')
    if author_element:
        data['author'] = author_element.text.strip()
    # Дата
    date_element = review.select_one('[data-testid="replay-header-date"]')
    if date_element:
        data['date'] = date_element.text.strip()
    # Основний текст
    text_element = review.select_one('.comment__body-wrapper p')
    if text_element:
        data['text'] = text_element.text.strip()
    # Переваги
    advantages_element = review.select_one('.comment__essentials dd')
    if advantages_element:
        data['advantages'] = advantages_element.text.strip()
    # Недоліки
    disadvantages_element = review.select_one('.comment__essentials dd:nth-of-type(2)')
    if disadvantages_element:
        data['disadvantages'] = disadvantages_element.text.strip()
    # Лайки/дизлайки
    likes_element = review.select_one('.vote-buttons-comments__counter')
    if likes_element:
        try:
            data['likes'] = int(likes_element.text.strip())
        except ValueError:
            pass
    dislikes_element = review.select_one('.vote-buttons-comments__vote--dislike .vote-buttons-comments__counter')
    if dislikes_element:
        try:
            data['dislikes'] = int(dislikes_element.text.strip())
        except ValueError:
            pass
    # Перевірка на покупку
    bought_element = review.select_one('[aria-label="uzhe_kupil"]')
    data['bought'] = bool(bought_element)
    # Фотографії
    photo_elements = review.select('.comment__photo, .comment__image')
    for photo in photo_elements:
        if 'src' in photo.attrs:
            data['comment_photos'].append(photo['src'])
    return data

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
        
    def extract_reviews(self, url: str) -> List[Dict[str, Any]]:
        """Extract reviews from product page using Playwright."""
        reviews = []
        
        logger.info("Починаємо витяг відгуків")
        
        with sync_playwright() as p:
            # Запускаємо браузер
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                # Відкриваємо сторінку
                page.goto(url)
                
                # Чекаємо поки завантажаться відгуки
                page.wait_for_selector('.product-comments__list-item')
                
                # Скролимо сторінку, щоб завантажити всі відгуки
                previous_height = 0
                max_scrolls = 10  # Максимальна кількість скролів
                scroll_count = 0
                
                while scroll_count < max_scrolls:
                    # Скролимо до кінця сторінки
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(2)  # Чекаємо поки підвантажаться нові відгуки
                    
                    # Перевіряємо нову висоту
                    current_height = page.evaluate('document.body.scrollHeight')
                    if current_height == previous_height:
                        break  # Якщо висота не змінилась, значить нові відгуки не завантажились
                        
                    previous_height = current_height
                    scroll_count += 1
                
                # Отримуємо HTML
                html = page.content()

                # Зберігаємо HTML для діагностики
                debug_path = os.path.abspath('debug_rozetka_product.html')
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"HTML сторінки збережено у: {debug_path}")
                print(f"Розмір debug_rozetka_product.html: {os.path.getsize(debug_path)} байт")
                print("Починаю парсинг відгуків з debug_rozetka_product.html...")
                
                # Аналізуємо відгуки
                soup = BeautifulSoup(html, 'html.parser')
                review_items = soup.select('.product-comments__list-item')
                logger.debug(f"Знайдено відгуків: {len(review_items)}")
                
                for item in review_items:
                    try:
                        review_data = extract_review_data(item)
                        reviews.append(review_data)
                        logger.debug(f"Додано відгук: {review_data}")
                    except Exception as e:
                        logger.error(f"Помилка при обробці відгуку: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"Помилка при роботі з Playwright: {str(e)}")
            finally:
                browser.close()
                
        logger.info(f"Загалом оброблено відгуків: {len(reviews)}")
        return reviews
        
    def extract_product_info(self, url: str) -> Dict[str, Any]:
        """Extract product information using Playwright."""
        product_info = {}
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                # Відкриваємо сторінку
                page.goto(url)
                
                # Чекаємо поки завантажиться заголовок
                page.wait_for_selector(self.config['selectors']['product_title'])
                
                # Отримуємо HTML
                html = page.content()
                
                # Аналізуємо дані
                soup = BeautifulSoup(html, 'lxml')
                
                # Шукаємо заголовок товару
                title_elem = soup.select_one(self.config['selectors']['product_title'])
                if title_elem:
                    product_info['title'] = title_elem.get_text(strip=True)
                    logger.info(f"Знайдено заголовок товару: {product_info['title']}")
                else:
                    logger.error("Заголовок товару не знайдено")
                    
            except Exception as e:
                logger.error(f"Помилка при роботі з Playwright: {str(e)}")
            finally:
                browser.close()
            
        return product_info 