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
            
            parser = config.get('parser', 'lxml')
            if isinstance(parser, dict):
                # config: {"type": "html", "config": {"parser": "lxml"}}
                parser = parser.get('config', {}).get('parser', 'lxml')
            soup = BeautifulSoup(html_content, parser)
            
            # Знаходимо назву товару
            product_title = None
            try:
                title_selector = config['selectors']['product']['title']['selector']
            except Exception:
                title_selector = config['selectors'].get('product_title')
            title_elem = soup.select_one(title_selector)
            if title_elem:
                product_title = title_elem.text.strip()
                current_app.logger.info(f"Знайдено назву товару: {product_title}")
            else:
                current_app.logger.warning(f"Не знайдено елемент з селектором '{title_selector}' для назви товару")
            
            # Знаходимо всі відгуки
            reviews = []
            try:
                container_selector = config['selectors']['reviews']['container']
                item_selector = config['selectors']['reviews']['item']
                fields_config = config['selectors']['reviews']['fields']
            except Exception:
                container_selector = config['selectors'].get('reviews_container')
                item_selector = config['selectors'].get('review_item')
                fields_config = config['selectors'].get('review_fields')
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
                    for field_name, selector_config in fields_config.items():
                        if isinstance(selector_config, dict):
                            selector = selector_config.get('selector')
                        else:
                            selector = selector_config
                        # --- Виправлення селекторів для рейтингу Rozetka та Prom ---
                        if field_name == 'rating':
                            if domain == 'rozetka.com.ua':
                                elem = item.select_one("[data-testid='stars-rating']")
                                if elem and elem.has_attr('style'):
                                    style = elem['style']
                                    m = re.search(r'width:\s*calc\((\d+)%\s*-\s*2px\)', style)
                                    if m:
                                        width = int(m.group(1))
                                        review[field_name] = width // 20
                                        current_app.logger.debug(f"Знайдено рейтинг через style: {review[field_name]}")
                                    else:
                                        review[field_name] = None
                                else:
                                    review[field_name] = None
                            elif domain == 'prom.ua':
                                elem = item.select_one("[data-qaid='count_stars']")
                                if elem and 'data-qaid-raiting' in elem.attrs:
                                    review[field_name] = int(elem['data-qaid-raiting']) // 20
                                else:
                                    review[field_name] = None
                            else:
                                elem = item.select_one(selector)
                                if elem:
                                    if isinstance(selector_config, dict) and selector_config.get('type') == 'style' and selector_config.get('attribute') == 'style' and 'pattern' in selector_config:
                                        style = elem.get('style', '')
                                        m = re.search(selector_config['pattern'], style)
                                        if m:
                                            width = int(m.group(1))
                                            review[field_name] = width // 20
                                        else:
                                            review[field_name] = None
                                    elif 'data-qaid-raiting' in elem.attrs:
                                        review[field_name] = int(elem['data-qaid-raiting']) // 20
                                    else:
                                        review[field_name] = None
                                else:
                                    review[field_name] = None
                        elif field_name == 'advantages':
                            elem = item.select_one("[data-qaid='pros']")
                        elif field_name == 'disadvantages':
                            elem = item.select_one("[data-qaid='cons']")
                        else:
                            elem = item.select_one(selector)
                        # --- кінець виправлення ---
                        if elem:
                            if field_name == 'rating':
                                # --- Парсимо рейтинг з width у style ---
                                if isinstance(selector_config, dict) and selector_config.get('type') == 'style' and selector_config.get('attribute') == 'style' and 'pattern' in selector_config:
                                    style = elem.get('style', '')
                                    m = re.search(selector_config['pattern'], style)
                                    if m:
                                        width = int(m.group(1))
                                        review[field_name] = width // 20
                                    else:
                                        review[field_name] = None
                                elif 'data-qaid-raiting' in elem.attrs:
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
    """Отримує HTML-код сторінки через Playwright (як у тесті)"""
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    import time
    import logging
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.goto(url)
                
                # Різні селектори для різних платформ
                if 'prom.ua' in url:
                    page.wait_for_selector('[data-qaid="opinion_item"]', timeout=30000)
                else:  # для rozetka
                    page.wait_for_selector('.product-comments__list-item', timeout=30000)
                
                previous_height = 0
                max_scrolls = 10
                scroll_count = 0
                while scroll_count < max_scrolls:
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(2)
                    current_height = page.evaluate('document.body.scrollHeight')
                    if current_height == previous_height:
                        break
                    previous_height = current_height
                    scroll_count += 1
                html = page.content()
                browser.close()
                return html
        except PlaywrightTimeoutError:
            logging.warning(f"PlaywrightTimeoutError для URL: {url}, спроба {attempt+1} з {max_attempts}")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            else:
                raise
        except Exception as e:
            logging.error(f"Playwright error для URL: {url}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            else:
                raise
    return None

def extract_rozetka_reviews_playwright(url):
    """Парсить відгуки Rozetka через Playwright, як у тесті, повертає product_title і reviews"""
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    import time
    from bs4 import BeautifulSoup
    import logging
    reviews = []
    product_title = None
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.goto(url)
                page.wait_for_selector('.product-comments__list-item', timeout=30000)
                previous_height = 0
                max_scrolls = 10
                scroll_count = 0
                while scroll_count < max_scrolls:
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(2)
                    current_height = page.evaluate('document.body.scrollHeight')
                    if current_height == previous_height:
                        break
                    previous_height = current_height
                    scroll_count += 1
                # --- Пошук тайтлу через кілька селекторів ---
                title_selectors = [
                    'h1.product__title',
                    '.product__heading',
                    '.product-title',
                    'h1',
                    'title'
                ]
                for sel in title_selectors:
                    title_elem = page.query_selector(sel)
                    if title_elem:
                        product_title = title_elem.inner_text().strip()
                        if product_title:
                            break
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                review_items = soup.select('.product-comments__list-item')
                for review in review_items:
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
                    rating_element = review.select_one('[data-testid="stars-rating"]')
                    if rating_element and 'style' in rating_element.attrs:
                        style = rating_element['style']
                        pattern = r'width:\s*calc\((\d+)%\s*-\s*2px\)'
                        m = re.search(pattern, style)
                        if m:
                            width = int(m.group(1))
                            data['rating'] = width // 20
                    author_element = review.select_one('[data-testid="replay-header-author"]')
                    if author_element:
                        data['author'] = author_element.text.strip()
                    date_element = review.select_one('[data-testid="replay-header-date"]')
                    if date_element:
                        data['date'] = date_element.text.strip()
                    text_element = review.select_one('.comment__body-wrapper p')
                    if text_element:
                        data['text'] = text_element.text.strip()
                    advantages_element = review.select_one('.comment__essentials dd')
                    if advantages_element:
                        data['advantages'] = advantages_element.text.strip()
                    disadvantages_element = review.select_one('.comment__essentials dd:nth-of-type(2)')
                    if disadvantages_element:
                        data['disadvantages'] = disadvantages_element.text.strip()
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
                    bought_element = review.select_one('[aria-label="uzhe_kupil"]')
                    data['bought'] = bool(bought_element)
                    photo_elements = review.select('.comment__photo, .comment__image')
                    for photo in photo_elements:
                        if 'src' in photo.attrs:
                            data['comment_photos'].append(photo['src'])
                    reviews.append(data)
                browser.close()
            break  # якщо все ок — виходимо з циклу
        except PlaywrightTimeoutError:
            logging.warning(f"PlaywrightTimeoutError для URL: {url}, спроба {attempt+1} з {max_attempts}")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            else:
                raise
        except Exception as e:
            logging.error(f"Playwright error для URL: {url}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
                continue
            else:
                raise
    return product_title, reviews

# --- Додаю використання цієї функції у ReviewExtractor ---

old_extract_reviews = ReviewExtractor.extract_reviews

def extract_reviews(self, html_content, url):
    if 'rozetka.com.ua' in url:
        product_title, reviews = extract_rozetka_reviews_playwright(url)
        return {
            'product_title': product_title,
            'reviews': reviews,
            'platform': 'rozetka.com.ua'
        }
    else:
        return old_extract_reviews(self, html_content, url)

ReviewExtractor.extract_reviews = extract_reviews 