from urllib.parse import urlparse
from datetime import datetime
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .ai_helper import AIHelper
import json
import requests
import yaml
import logging
from lxml import html as lxml_html
from flask import current_app
from urllib.parse import urljoin
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ai_helper = AIHelper()

class ReviewExtractor:
    def __init__(self):
        self.common_patterns = {
            'product_title': [
                'h1.title__font',
                'h1.product__title',
                'h1.title',
                'div.product-title h1',
                'div[data-qaid="product_name"]'
            ],
            'reviews_container': [
                'div.product-comments__list',
                'div.reviews-list',
                'div.product-reviews',
                'div[data-qaid="comments_list"]',
                'div.comments-list',
                'section.reviews'
            ],
            'review_item': [
                'div.comment__inner',
                'div.review-item',
                'div.comment-item',
                'div.review',
                'article.review'
            ],
            'author': [
                'div[data-testid="replay-header-author"]',
                'span.author-name',
                'div.user-name',
                'div.reviewer-name',
                'span.user'
            ],
            'rating': [
                'div[data-testid="stars-rating"]',
                'div.rating-value',
                'span.stars',
                'div[data-rating]',
                'div.star-rating'
            ],
            'text': [
                'div.comment__body',
                'div.review-text',
                'div.comment-text',
                'p.review-content',
                'div.text'
            ],
            'date': [
                'time[data-testid="replay-header-date"]',
                'time.review-date',
                'div.review-time',
                'span.date',
                'div.review-date'
            ],
            'advantages': [
                'div[data-qaid="pros"]',
                'div.comment__advantages',
                'div.advantages',
                'div.plus',
                'div.pros'
            ],
            'disadvantages': [
                'div[data-qaid="cons"]',
                'div.comment__disadvantages',
                'div.disadvantages',
                'div.minus',
                'div.cons'
            ]
        }
        
        # Додаткові патерни для конкретних платформ
        self.platform_patterns = {
            'rozetka': {
                'product_title': ['h1.title__font'],
                'reviews_container': ['div.product-comments__list'],
                'review_item': ['div.comment__inner'],
                'author': ['div[data-testid="replay-header-author"]'],
                'rating': ['div[data-testid="stars-rating"]'],
                'text': ['div.comment__body'],
                'date': ['time[data-testid="replay-header-date"]'],
                'advantages': ['div.comment__advantages'],
                'disadvantages': ['div.comment__disadvantages']
            },
            'prom': {
                'product_title': ['h1[data-qaid="page_title"]'],
                'reviews_container': ['div[data-qaid="opinion_list"]'],
                'review_item': ['div[data-qaid="opinion_item"]'],
                'author': ['div[data-qaid="opinion_author"]'],
                'rating': ['div[data-qaid="opinion_rating"]'],
                'text': ['div[data-qaid="opinion_text"]'],
                'date': ['time[data-qaid="opinion_date"]']
            }
        }

    def find_element(self, soup, patterns):
        """Шукає елемент за списком можливих селекторів"""
        for selector in patterns:
            element = soup.select_one(selector)
            if element:
                return element
        return None

    def find_elements(self, soup, patterns):
        """Шукає всі елементи за списком можливих селекторів"""
        for selector in patterns:
            elements = soup.select(selector)
            if elements:
                return elements
        return []

    def detect_platform(self, url):
        """Визначає платформу за URL"""
        if 'rozetka.com.ua' in url:
            return 'rozetka'
        elif 'prom.ua' in url:
            return 'prom'
        return 'unknown'

    def extract_reviews(self, html_content, url):
        """Витягує відгуки з HTML контенту"""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
                
            current_app.logger.info(f"Шукаємо конфігурацію для домену: {domain}")
            
            # Спочатку шукаємо в базі даних
            from app.models.platform import Platform
            platform_config = Platform.query.filter(Platform.domain.like(f"%{domain}%")).first()
            
            if platform_config and platform_config.config:
                try:
                    config = json.loads(platform_config.config)
                except json.JSONDecodeError:
                    current_app.logger.error("Помилка декодування JSON конфігурації з бази даних")
                    config = None
            else:
                config = None
                
            if not config:
                # Якщо в базі немає або помилка, використовуємо конфігурацію з файлу
                from app.extractors.factory import ExtractorFactory
                platform = self.detect_platform(url)
                extractor = ExtractorFactory.create_extractor(platform)
                if not extractor:
                    raise Exception(f"Не знайдено екстрактор для платформи {platform}")
                config = extractor.config
            
            current_app.logger.info(f"Використовуємо конфігурацію: {json.dumps(config, ensure_ascii=False)}")
            
            soup = BeautifulSoup(html_content, config.get('parser', 'lxml'))
            
            # Знаходимо назву товару
            product_title = None
            title_selector = config['selectors']['product_title']
            title_elem = soup.select_one(title_selector)
            if title_elem:
                product_title = title_elem.text.strip()
                current_app.logger.info(f"Знайдено назву товару: {product_title}")
            else:
                current_app.logger.warning(f"Не знайдено елемент з селектором '{title_selector}' для назви товару")
            
            # Знаходимо всі відгуки
            reviews = []
            container_selector = config['selectors']['reviews_container']
            item_selector = config['selectors']['review_item']
            
            # Логуємо HTML контейнера відгуків
            reviews_container = soup.select_one(container_selector)
            if reviews_container:
                current_app.logger.info(f"Знайдено контейнер відгуків. HTML: {reviews_container.prettify()[:500]}...")
            else:
                current_app.logger.warning(f"Не знайдено контейнер відгуків з селектором '{container_selector}'")
            
            review_items = soup.select(f"{container_selector} {item_selector}")
            current_app.logger.info(f"Знайдено відгуків: {len(review_items)}")
            
            if len(review_items) == 0:
                current_app.logger.warning(f"Не знайдено відгуків за селектором '{container_selector} {item_selector}'")
                # Перевіряємо наявність елементів окремо
                all_containers = soup.select(container_selector)
                current_app.logger.info(f"Кількість знайдених контейнерів: {len(all_containers)}")
                all_items = soup.select(item_selector)
                current_app.logger.info(f"Кількість знайдених елементів відгуків: {len(all_items)}")
                # Якщо контейнерів немає, але є елементи — використовуємо їх
                if len(all_items) > 0:
                    review_items = all_items
                    current_app.logger.info(f"Використовуємо всі знайдені елементи відгуків на сторінці: {len(review_items)}")
            
            for item in review_items:
                try:
                    review = {
                        'platform': domain,
                        'advantages': None,
                        'disadvantages': None
                    }
                    
                    # Витягуємо всі поля згідно конфігурації
                    fields_config = config['selectors']['review_fields']
                    for field_name, selector in fields_config.items():
                        elem = item.select_one(selector)
                        if elem:
                            if field_name == 'rating':
                                if 'data-qaid-raiting' in elem.attrs:
                                    review[field_name] = int(elem['data-qaid-raiting']) // 20
                                else:
                                    review[field_name] = None
                            else:
                                review[field_name] = elem.text.strip()
                            current_app.logger.debug(f"Для поля '{field_name}' знайдено значення: {review[field_name]}")
                        else:
                            current_app.logger.warning(f"Не знайдено елемент з селектором '{selector}' для поля '{field_name}'")
                            review[field_name] = None
                    
                    if review.get('author') or review.get('title'):
                        reviews.append(review)
                        current_app.logger.debug(f"Оброблено відгук: {json.dumps(review, ensure_ascii=False)}")
                    
                except Exception as e:
                    current_app.logger.error(f"Помилка при обробці відгуку: {str(e)}")
                    continue
            
            return {
                'product_title': product_title,
                'reviews': reviews,
                'platform': domain
            }
            
        except Exception as e:
            current_app.logger.error(f"Помилка при витягуванні відгуків: {str(e)}")
            raise

    def extract_prom_reviews(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract reviews from Prom.ua using the same logic as the test file
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        reviews = []
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find all reviews using stable data-qaid
            review_items = soup.find_all('div', attrs={'data-qaid': 'opinion_item'})
            
            self.logger.info(f"Found {len(review_items)} reviews")
            
            for item in review_items:
                review = {}
                
                # Author
                author_elem = item.find('span', attrs={'data-qaid': 'author_name'})
                if author_elem:
                    review['author'] = author_elem.text.strip()
                
                # Date
                date_elem = item.find('time', attrs={'data-qaid': 'date_created'})
                if date_elem:
                    review['date'] = self.parse_prom_date(date_elem.text.strip())
                
                # Rating (search by svg with data-qaid="count_stars")
                rating_elem = item.find('svg', attrs={'data-qaid': 'count_stars'})
                if rating_elem and 'data-qaid-raiting' in rating_elem.attrs:
                    review['rating'] = int(rating_elem['data-qaid-raiting']) // 20  # Convert from percentage to stars
                
                # Review title/text
                title_elem = item.find('span', attrs={'data-qaid': 'title'})
                if title_elem:
                    review['text'] = title_elem.text.strip()
                
                # Verified purchase check
                purchase_elem = item.find('span', attrs={'data-qaid': 'prom_label_text'})
                review['verified_purchase'] = bool(purchase_elem)
                
                # Review ID
                if 'data-qaopinionid' in item.attrs:
                    review['platform_review_id'] = item['data-qaopinionid']
                
                # Only add reviews that have at least some content
                if any(review.values()):
                    reviews.append(review)
                    self.logger.debug(f"Processed review: {json.dumps(review, ensure_ascii=False)}")
            
            return reviews
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching reviews: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing reviews: {str(e)}")
            return []

def extract_google_reviews(page, max_reviews):
    """Extract reviews from Google Maps"""
    reviews = []
    
    try:
        # Чекаємо на завантаження відгуків
        page.wait_for_selector('.review-full-text', timeout=60000)
        
        # Прокручуємо сторінку, щоб завантажити більше відгуків
        for _ in range(3):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(1000)
        
        # Витягуємо відгуки
        review_elements = page.query_selector_all('.review-item')
        for element in review_elements[:max_reviews]:
            try:
                review = {
                    'platform': 'google',
                    'author': element.query_selector('.author-name').inner_text(),
                    'text': element.query_selector('.review-full-text').inner_text(),
                    'rating': float(element.get_attribute('data-rating')),
                    'date': parse_google_date(element.query_selector('.review-date').inner_text()),
                    'platform_review_id': element.get_attribute('data-review-id')
                }
                reviews.append(review)
            except Exception as e:
                print(f'Error extracting review: {str(e)}')
                continue
    
    except Exception as e:
        raise Exception(f'Error extracting Google reviews: {str(e)}')
    
    return reviews

def test_extract_prom_reviews(url):
    """
    Тестовий парсер для відгуків з Prom.ua - точна копія робочого тестового скрипта
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    reviews = []
    try:
        # Отримуємо сторінку відгуків
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Знаходимо назву товару прямо на сторінці відгуків
        product_title = None
        title_elem = soup.find('h1', attrs={'data-qaid': 'page_title'})
        if title_elem:
            product_title = title_elem.text.strip()
            current_app.logger.info(f"Знайдено назву товару: {product_title}")
        
        # Знаходимо всі відгуки за стабільним data-qaid
        review_items = soup.find_all('div', attrs={'data-qaid': 'opinion_item'})
        
        current_app.logger.info(f"Знайдено відгуків через тестовий парсер: {len(review_items)}")
        
        for item in review_items:
            try:
                review = {}
                
                # Автор
                author_elem = item.find('span', attrs={'data-qaid': 'author_name'})
                review['author'] = author_elem.text.strip() if author_elem else None
                
                # Дата
                date_elem = item.find('time', attrs={'data-qaid': 'date_created'})
                review['date'] = date_elem.text.strip() if date_elem else None
                
                # Рейтинг
                rating_elem = item.find('svg', attrs={'data-qaid': 'count_stars'})
                if rating_elem and 'data-qaid-raiting' in rating_elem.attrs:
                    review['rating'] = int(rating_elem['data-qaid-raiting']) // 20
                else:
                    review['rating'] = None
                
                # Текст
                title_elem = item.find('span', attrs={'data-qaid': 'title'})
                review['text'] = title_elem.text.strip() if title_elem else None
                
                # ID відгуку
                review['platform_review_id'] = item.get('data-qaopinionid', '')
                
                # Платформа
                review['platform'] = 'prom'
                
                # Додаємо порожні поля для advantages та disadvantages
                review['advantages'] = None
                review['disadvantages'] = None
                
                if review['author'] or review['text']:
                    reviews.append(review)
                    current_app.logger.debug(f"Оброблено відгук через тестовий парсер: {json.dumps(review, ensure_ascii=False, indent=2)}")
                
            except Exception as e:
                current_app.logger.error(f"Помилка при парсингу відгуку в тестовому парсері: {str(e)}")
                continue
                
        return product_title, reviews
        
    except Exception as e:
        current_app.logger.error(f"Помилка в тестовому парсері: {str(e)}")
        return None, []

def extract_prom_reviews(page, max_reviews):
    """Extract reviews from Prom.ua"""
    try:
        # Отримуємо URL
        url = page.url
        current_app.logger.info(f"Починаємо парсинг відгуків з URL: {url}")
        
        # Використовуємо тестовий парсер
        product_title, reviews = test_extract_prom_reviews(url)
        
        # Обмежуємо кількість відгуків якщо потрібно
        if max_reviews:
            reviews = reviews[:max_reviews]
            
        return reviews
        
    except Exception as e:
        current_app.logger.error(f"Помилка при витягуванні відгуків: {str(e)}")
        return []

def extract_rozetka_reviews(page, max_reviews):
    """Extract reviews from Rozetka"""
    reviews = []
    
    try:
        # Чекаємо на завантаження відгуків
        page.wait_for_selector('.comment', timeout=60000)
        
        # Прокручуємо сторінку для завантаження більше відгуків
        for _ in range(3):
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(1000)
        
        # Витягуємо відгуки
        review_elements = page.query_selector_all('.comment')
        for element in review_elements[:max_reviews]:
            try:
                review = {
                    'platform': 'rozetka',
                    'author': element.query_selector('.comment-author').inner_text(),
                    'text': element.query_selector('.comment-text').inner_text(),
                    'rating': float(element.query_selector('.rating').get_attribute('data-rating')),
                    'date': parse_rozetka_date(element.query_selector('time.product-review__date').inner_text()),
                    'platform_review_id': element.get_attribute('data-comment-id')
                }
                reviews.append(review)
            except Exception as e:
                print(f'Error extracting review: {str(e)}')
                continue
    
    except Exception as e:
        raise Exception(f'Error extracting Rozetka reviews: {str(e)}')
    
    return reviews

def parse_google_date(date_str):
    """Parse Google review date"""
    # Example implementation
    return datetime.now()  # TODO: Implement proper date parsing

def parse_prom_date(date_str):
    """Parse Prom.ua review date"""
    try:
        # Prom використовує формат "DD.MM.YYYY"
        return datetime.strptime(date_str.strip(), "%d.%m.%Y")
    except ValueError as e:
        current_app.logger.error(f"Error parsing Prom date '{date_str}': {str(e)}")
        return None

def parse_rozetka_date(date_str):
    """Parse Rozetka review date"""
    try:
        # Rozetka використовує формат "DD місяць YYYY"
        months = {
            'січня': '01', 'лютого': '02', 'березня': '03', 'квітня': '04',
            'травня': '05', 'червня': '06', 'липня': '07', 'серпня': '08',
            'вересня': '09', 'жовтня': '10', 'листопада': '11', 'грудня': '12'
        }
        
        # Розбиваємо рядок на день, місяць та рік
        parts = date_str.strip().split()
        if len(parts) != 3:
            raise ValueError(f"Invalid date format: {date_str}")
            
        day = parts[0]
        month = months.get(parts[1].lower())
        year = parts[2]
        
        if not month:
            raise ValueError(f"Unknown month: {parts[1]}")
            
        return datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y")
    except Exception as e:
        current_app.logger.error(f"Error parsing Rozetka date '{date_str}': {str(e)}")
        return None

def extract_page_content(url):
    """Отримує HTML-код сторінки"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://allo.ua/'
        }

        # Додаємо cookies для більшої схожості на реального користувача
        cookies = {
            'locale': 'uk',
            'currency': 'UAH',
            'city': 'Kyiv'
        }
        
        # Робимо запит з таймаутом
        response = requests.get(
            url,
            headers=headers,
            cookies=cookies,
            timeout=10,
            allow_redirects=True,
            verify=False
        )
        
        response.raise_for_status()
        
        # Перевіряємо кодування
        if 'charset' in response.headers.get('content-type', '').lower():
            response.encoding = response.apparent_encoding
        else:
            response.encoding = 'utf-8'
            
        return response.text
        
    except Exception as e:
        current_app.logger.error(f"Error fetching page content: {str(e)}")
        return None 