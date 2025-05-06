import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
import json
import time
import random
from flask import current_app
from io import StringIO
import logging
from bs4.element import Tag

logger = logging.getLogger(__name__)

class AIHelper:
    def __init__(self, base_url: str = "http://127.0.0.1:5500/", max_retries: int = 5, retry_delay: int = 5):
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_chunk_size = 2000
        self.logger = logging.getLogger(__name__)

    def _make_request_with_retry(self, prompt):
        """Відправляє запит до локального ШІ сервісу з повторними спробами"""
        for attempt in range(1, self.max_retries + 1):
            try:
                # Створюємо файл з текстом промпту
                files = {
                    'file': ('prompt.txt', prompt, 'text/plain')
                }
                response = requests.post(
                    self.base_url,
                    files=files,
                    timeout=30
                )
                response.raise_for_status()
                
                # Отримуємо текст відповіді
                response_text = response.text.strip()
                
                # Логуємо відповідь для дебагу
                current_app.logger.debug(f"AI response: {response_text[:200]}...")
                
                if not response_text:
                    raise ValueError("Empty response from AI service")
                    
                # Перевіряємо чи це валідний JSON
                try:
                    json.loads(response_text)
                    return response_text
                except json.JSONDecodeError:
                    # Якщо не JSON, шукаємо JSON в тексті
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    if start >= 0 and end > start:
                        json_str = response_text[start:end]
                        # Перевіряємо що це валідний JSON
                        json.loads(json_str)
                        return json_str
                    raise ValueError(f"Invalid JSON in response: {response_text[:200]}...")
                    
            except requests.RequestException as e:
                current_app.logger.warning(
                    f"Request failed (attempt {attempt}/{self.max_retries}): {str(e)}"
                )
                if attempt == self.max_retries:
                    raise
                time.sleep(self.retry_delay)
            except (ValueError, json.JSONDecodeError) as e:
                current_app.logger.error(f"Error processing response: {str(e)}")
                if attempt == self.max_retries:
                    raise
                time.sleep(self.retry_delay)

    def analyze_title_block(self, html_content: str) -> str:
        """Аналізує HTML блок з назвою товару та повертає селектор"""
        try:
            prompt = f"""Проаналізуй HTML код блоку з назвою товару та поверни CSS селектор.
            
            HTML код:
            {html_content}
            
            Поверни тільки селектор без пояснень."""
            
            response = self._make_request_with_retry(prompt)
            
            # Видаляємо можливі markdown-теги для коду та зайві пробіли
            response = response.replace('```css', '').replace('```', '').strip()
            
            # Повертаємо селектор як є, без спроби парсити JSON
            return response
            
        except Exception as e:
            self.logger.error(f"Помилка при аналізі заголовку: {str(e)}")
            raise

    def analyze_review_block(self, html_content):
        """Аналізує HTML блок відгуку та повертає структуру селекторів"""
        try:
            prompt = f"""Проаналізуй HTML блок відгуку та поверни конфігурацію для парсингу в форматі JSON.
            HTML блок:
            {html_content}
            
            Потрібно повернути JSON в такому форматі:
            {{
                "parser": {{
                    "type": "html",
                    "config": {{
                        "parser": "lxml"
                    }}
                }},
                "selectors": {{
                    "product": {{
                        "title": {{
                            "selector": "СЕЛЕКТОР_ЗАГОЛОВКА",
                            "type": "text"
                        }}
                    }},
                    "reviews": {{
                        "container": "СЕЛЕКТОР_КОНТЕЙНЕРА_ВІДГУКІВ",
                        "item": "СЕЛЕКТОР_ЕЛЕМЕНТА_ВІДГУКУ",
                        "fields": {{
                            "author": {{
                                "selector": "СЕЛЕКТОР_АВТОРА",
                                "type": "text"
                            }},
                            "date": {{
                                "selector": "СЕЛЕКТОР_ДАТИ",
                                "type": "text"
                            }},
                            "rating": {{
                                "selector": "СЕЛЕКТОР_РЕЙТИНГУ",
                                "type": "number"
                            }},
                            "text": {{
                                "selector": "СЕЛЕКТОР_ТЕКСТУ",
                                "type": "text"
                            }},
                            "advantages": {{
                                "selector": "СЕЛЕКТОР_ПЕРЕВАГ",
                                "type": "text"
                            }},
                            "disadvantages": {{
                                "selector": "СЕЛЕКТОР_НЕДОЛІКІВ",
                                "type": "text"
                            }}
                        }}
                    }}
                }}
            }}
            
            Правила:
            1. Знайди всі необхідні CSS селектори в HTML
            2. Для container - знайди батьківський елемент, який містить всі відгуки
            3. Для item - знайди селектор окремого відгуку
            4. Для полів (author, date, rating і т.д.) - знайди відповідні селектори всередині item
            5. Якщо якийсь селектор не знайдено - використовуй null замість порожнього рядка
            6. Використовуй точні селектори з HTML, не вигадуй їх
            7. Для рейтингу вкажи type: "number"
            8. Для всіх інших полів вкажи type: "text"
            9. НЕ ВИКОРИСТОВУЙ порожні рядки для селекторів!
            
            Поверни тільки JSON без пояснень."""

            response = self._make_request_with_retry(prompt)
            if not response:
                raise Exception("Не вдалося отримати відповідь від AI")
            
            # Перевіряємо, що відповідь - валідний JSON
            config = json.loads(response)
            
            # Перевіряємо наявність всіх необхідних полів
            if not all(key in config for key in ['parser', 'selectors']):
                raise Exception("Відсутні обов'язкові поля в конфігурації")
            
            if not all(key in config['selectors'] for key in ['product', 'reviews']):
                raise Exception("Відсутні обов'язкові секції в селекторах")
            
            if not all(key in config['selectors']['reviews'] for key in ['container', 'item', 'fields']):
                raise Exception("Відсутні обов'язкові поля в секції reviews")
            
            required_fields = ['author', 'date', 'rating', 'text', 'advantages', 'disadvantages']
            if not all(field in config['selectors']['reviews']['fields'] for field in required_fields):
                raise Exception("Відсутні обов'язкові поля в конфігурації відгуків")
            
            # Замінюємо null або порожні рядки на значення за замовчуванням
            if not config['selectors']['product']['title']['selector']:
                config['selectors']['product']['title']['selector'] = 'h1'
            
            for field in required_fields:
                if not config['selectors']['reviews']['fields'][field]['selector']:
                    if field == 'advantages':
                        config['selectors']['reviews']['fields'][field]['selector'] = '.advantages, .pros, [data-test-id="plus"]'
                    elif field == 'disadvantages':
                        config['selectors']['reviews']['fields'][field]['selector'] = '.disadvantages, .cons, [data-test-id="minus"]'
                    else:
                        config['selectors']['reviews']['fields'][field]['selector'] = f'.{field}'
            
            return config
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Помилка при парсингу JSON: {str(e)}")
            raise Exception("Неправильний формат JSON у відповіді")
        except Exception as e:
            current_app.logger.error(f"Помилка при аналізі відгуку: {str(e)}")
            raise

    def generate_platform_config(self, url: str, title_selector: str, review_selectors: Dict[str, str]) -> Dict[str, Any]:
        """Генерує повну конфігурацію платформи"""
        try:
            config = {
                "parser": {
                    "type": "html",
                    "config": {
                        "parser": "lxml"
                    }
                },
                "selectors": {
                    "product": {
                        "title": {
                            "selector": title_selector.strip('`'),  # Видаляємо зайві символи ` якщо вони є
                            "type": "text"
                        }
                    },
                    "reviews": {
                        "container": "div.product-comments",
                        "item": "div.product-comment",
                        "fields": {}
                    }
                }
            }
            
            # Додаємо поля відгуків
            field_types = {
                "rating": "number",
                "text": "text",
                "author": "text",
                "date": "text",
                "advantages": "text",
                "disadvantages": "text"
            }
            
            for field, selector in review_selectors.items():
                if field in field_types:
                    config["selectors"]["reviews"]["fields"][field] = {
                        "selector": selector.strip('`'),  # Видаляємо зайві символи ` якщо вони є
                        "type": field_types[field]
                    }
                    
                    # Додаємо converter для рейтингу якщо потрібно
                    if field == "rating" and "user__rating--estimate" in selector:
                        config["selectors"]["reviews"]["fields"][field]["converter"] = "divide_by_20"
            
            return config
            
        except Exception as e:
            self.logger.error(f"Помилка при генерації конфігурації: {str(e)}")
            raise

    def _extract_domain(self, url: str) -> str:
        """Витягує домен з URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc.split('.')[-2]

    def _split_text(self, text: str) -> list:
        """Розбиває текст на менші частини, зберігаючи цілісність речень"""
        if len(text) <= self.max_chunk_size:
            return [text]

        chunks = []
        current_chunk = ""
        sentences = text.split('\n')

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.max_chunk_size:
                current_chunk += sentence + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '\n'

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _combine_responses(self, responses: List[str]) -> str:
        """Комбінує відповіді від різних чанків"""
        try:
            combined = []
            for response in responses:
                try:
                    data = json.loads(response)
                    if isinstance(data, dict):
                        combined.append(data)
                except:
                    continue

            if not combined:
                return responses[0]

            # Об'єднуємо всі знайдені селектори
            result = combined[0]
            for data in combined[1:]:
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key not in result:
                            result[key] = value

            return json.dumps(result)
        except Exception as e:
            self.logger.error(f"Error combining responses: {str(e)}")
            return responses[0]

    def _extract_structured_data(self, response):
        """Витягує структуровані дані (JSON або YAML) з відповіді AI"""
        try:
            # Спочатку спробуємо розпарсити як чистий JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass

            # Шукаємо JSON в форматованому блоці
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if start >= 7 and end > start:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)

            # Шукаємо YAML в форматованому блоці
            if "```yaml" in response:
                try:
                    import yaml
                    start = response.find("```yaml") + 7
                    end = response.find("```", start)
                    if start >= 7 and end > start:
                        yaml_str = response[start:end].strip()
                        return yaml.safe_load(yaml_str)
                except ImportError:
                    current_app.logger.warning("PyYAML not installed, skipping YAML parsing")
                except Exception as e:
                    current_app.logger.error(f"Error parsing YAML: {str(e)}")

            # Шукаємо JSON між фігурними дужками
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                # Видаляємо коментарі та пояснення всередині JSON
                lines = json_str.split('\n')
                clean_lines = [line for line in lines if not line.strip().startswith('//') and not line.strip().startswith('/*')]
                json_str = '\n'.join(clean_lines)
                return json.loads(json_str)

            raise ValueError("No structured data (JSON/YAML) found in response")
        except Exception as e:
            self.logger.error(f"Error extracting structured data from response: {str(e)}\nResponse: {response[:200]}...")
            return None

    def analyze_page_structure(self, html_content):
        """Аналізує структуру HTML сторінки та повертає базові селектори"""
        try:
            prompt = self.analyze_structure_prompt.format(html=html_content)
            response = self._make_request_with_retry(prompt)
            
            if not response:
                current_app.logger.error("Failed to get response from AI service")
                return None
                
            # Очищуємо відповідь від додаткового тексту
            cleaned_response = self._clean_ai_response(response)
            
            # Витягуємо структуровані дані з очищеної відповіді
            result = self._extract_structured_data(cleaned_response)
            
            if not result:
                current_app.logger.error("Failed to extract structured data from AI response")
                return None
                
            # Перевіряємо наявність необхідних полів
            if isinstance(result, dict):
                if 'selectors' in result:
                    return result['selectors']
                return result
            
            current_app.logger.error(f"Unexpected response format: {result}")
            return None
                
        except Exception as e:
            current_app.logger.error(f"Error analyzing page structure: {str(e)}")
            return None

    def analyze_review_structure(self, html):
        """Аналізує структуру блоку відгуку та повертає селектори для полів"""
        prompt = f"""Проаналізуй HTML-код блоку відгуку та визнач CSS селектори для наступних полів:
1. Ім'я автора
2. Текст відгуку
3. Рейтинг (зірки/оцінка)
4. Дата відгуку
5. Переваги (якщо є)
6. Недоліки (якщо є)

Поверни результат у форматі JSON:
{{
    "author": "css_selector",
    "text": "css_selector",
    "rating": "css_selector",
    "date": "css_selector",
    "advantages": "css_selector",
    "disadvantages": "css_selector"
}}

HTML код:
{html}
"""
        
        try:
            response = self._make_request_with_retry(prompt)
            if not response:
                current_app.logger.error("Failed to get response from AI service")
                return None
                
            # Очищуємо відповідь від додаткового тексту
            cleaned_response = self._clean_ai_response(response)
            
            # Витягуємо структуровані дані з очищеної відповіді
            result = self._extract_structured_data(cleaned_response)
            
            if not result:
                current_app.logger.error("Failed to extract structured data from AI response")
                return None
                
            return result
                
        except Exception as e:
            current_app.logger.error(f"Error analyzing review structure: {str(e)}")
            return None

    def _extract_json_from_response(self, response):
        """Витягує JSON з текстової відповіді AI"""
        try:
            # Спочатку спробуємо розпарсити як чистий JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass

            # Шукаємо JSON в форматованому блоці
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if start >= 7 and end > start:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)

            # Шукаємо JSON між фігурними дужками
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                # Видаляємо коментарі та пояснення всередині JSON
                lines = json_str.split('\n')
                clean_lines = [line for line in lines if not line.strip().startswith('//') and not line.strip().startswith('/*')]
                json_str = '\n'.join(clean_lines)
                return json.loads(json_str)

            raise ValueError("JSON not found in response")
        except Exception as e:
            current_app.logger.error(f"Error extracting JSON from response: {str(e)}\nResponse: {response[:200]}...")
            raise ValueError(f"Failed to parse JSON from response: {str(e)}")

    def _clean_ai_response(self, response):
        """Очищує відповідь AI від додаткового тексту та форматування"""
        # Видаляємо markdown форматування
        response = response.replace('```json', '').replace('```', '')
        
        # Видаляємо пояснення та коментарі
        lines = response.split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            if '{' in line:
                in_json = True
            if in_json:
                json_lines.append(line)
            if '}' in line:
                in_json = False
                
        if json_lines:
            return '\n'.join(json_lines)
        return response

    def _generate_prompt(self, platform):
        """Генерує промпт для обробки відгуків з різних платформ"""
        if platform == 'rozetka':
            return """
            Проаналізуй відгук з Rozetka та витягни наступну інформацію у форматі JSON:
            {
                "author": "ім'я автора",
                "text": "текст відгуку",
                "rating": число від 1 до 5,
                "date": "дата у форматі YYYY-MM-DD",
                "advantages": "переваги товару",
                "disadvantages": "недоліки товару"
            }
            """
        elif platform == 'prom':
            return """
            Проаналізуй відгук з Prom.ua та витягни наступну інформацію у форматі JSON:
            {
                "author": "ім'я автора",
                "text": "текст відгуку",
                "rating": число від 1 до 5,
                "date": "дата у форматі YYYY-MM-DD",
                "advantages": "переваги товару",
                "disadvantages": "недоліки товару"
            }
            Поверни тільки чистий JSON без додаткового тексту.
            """
        else:
            return """
            Проаналізуй відгук та витягни наступну інформацію у форматі JSON:
            {
                "author": "ім'я автора",
                "text": "текст відгуку",
                "rating": число від 1 до 5,
                "date": "дата"
            }
            """

    def extract_reviews_from_html(self, html_content: str, platform: str) -> dict:
        """
        Використовує ШІ для витягування відгуків з HTML контенту
        """
        # Попередня обробка HTML для зменшення розміру
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Видаляємо непотрібні елементи
        for tag in soup(['script', 'style', 'meta', 'link']):
            tag.decompose()
        
        # Спробуємо витягти дані з HTML самостійно
        if platform == 'rozetka':
            reviews = []
            comments = soup.find_all('div', class_='comment')
            
            # Варіанти написання переваг та недоліків різними мовами
            pros_variants = ['Достоинства:', 'Переваги:', 'Advantages:', 'Pros:', 'Плюсы:']
            cons_variants = ['Недостатки:', 'Недоліки:', 'Disadvantages:', 'Cons:', 'Минусы:']
            
            for comment in comments:
                try:
                    author = comment.find('div', attrs={'data-testid': 'replay-header-author'})
                    comment_body = comment.find('div', class_='comment__body')
                    
                    # Знаходимо основний текст, переваги та недоліки
                    text_elem = comment_body.find('p') if comment_body else None
                    
                    # Шукаємо переваги за всіма можливими варіантами
                    pros_elem = None
                    for pros_text in pros_variants:
                        pros_elem = comment_body.find('div', string=lambda x: x and pros_text in x) if comment_body else None
                        if pros_elem:
                            break
                    
                    # Шукаємо недоліки за всіма можливими варіантами
                    cons_elem = None
                    for cons_text in cons_variants:
                        cons_elem = comment_body.find('div', string=lambda x: x and cons_text in x) if comment_body else None
                        if cons_elem:
                            break
                    
                    rating_elem = comment.find('div', attrs={'data-testid': 'stars-rating'})
                    date_elem = comment.find('time', attrs={'data-testid': 'replay-header-date'})
                    
                    if author and comment_body:
                        # Збираємо всі частини відгуку
                        text_parts = []
                        
                        # Додаємо основний текст
                        if text_elem and text_elem.text.strip():
                            text_parts.append(text_elem.text.strip())
                        
                        # Додаємо переваги
                        if pros_elem:
                            pros_text = pros_elem.text.strip()
                            # Знаходимо, який варіант заголовку використовується
                            used_pros_header = next((h for h in pros_variants if h in pros_text), 'Переваги:')
                            # Видаляємо заголовок і зайві пробіли
                            pros_content = pros_text.replace(used_pros_header, '').strip()
                            if pros_content:
                                text_parts.append(f"{used_pros_header} {pros_content}")
                        
                        # Додаємо недоліки
                        if cons_elem:
                            cons_text = cons_elem.text.strip()
                            # Знаходимо, який варіант заголовку використовується
                            used_cons_header = next((h for h in cons_variants if h in cons_text), 'Недоліки:')
                            # Видаляємо заголовок і зайві пробіли
                            cons_content = cons_text.replace(used_cons_header, '').strip()
                            if cons_content:
                                text_parts.append(f"{used_cons_header} {cons_content}")
                        
                        # Формуємо повний текст відгуку
                        full_text = '\n'.join(text_parts)
                        
                        rating = 0
                        if rating_elem:
                            style = rating_elem.get('style', '')
                            if 'width: calc(100%' in style:
                                rating = 5
                            elif 'width: calc(80%' in style:
                                rating = 4
                            elif 'width: calc(60%' in style:
                                rating = 3
                            elif 'width: calc(40%' in style:
                                rating = 2
                            elif 'width: calc(20%' in style:
                                rating = 1
                        
                        reviews.append({
                            'author': author.text.strip(),
                            'text': full_text,
                            'rating': rating,
                            'date': date_elem.text.strip() if date_elem else None,
                            'platform_review_id': comment.get('data-comment-id', '')
                        })
                except Exception as e:
                    print(f"Error extracting data from comment: {str(e)}")
                    continue
            
            if reviews:
                return {'reviews': reviews}
        
        # Якщо не вдалося витягти дані самостійно, спробуємо через ШІ
        try:
            # Генеруємо промт
            prompt = self._generate_prompt(platform)
            
            # Відправляємо запит з HTML елементом з повторними спробами
            response_text = self._make_request_with_retry(f"{prompt}\n\n{str(soup)}")
            
            try:
                # Спробуємо спочатку розпарсити як JSON
                result = json.loads(response_text)
                
                # Якщо результат - словник з reviews
                if isinstance(result, dict) and 'reviews' in result:
                    return result
                    
                # Якщо результат - список
                elif isinstance(result, list):
                    return {'reviews': result}
                    
                # Якщо результат - словник без reviews
                elif isinstance(result, dict):
                    return {'reviews': [result]}
                    
                # Якщо результат - інший тип даних
                else:
                    return {
                        'reviews': [{
                            'author': 'Unknown',
                            'text': str(result),
                            'rating': 0,
                            'date': None,
                            'platform_review_id': None
                        }]
                    }
                    
            except json.JSONDecodeError:
                # Якщо не вдалося розпарсити JSON, спробуємо знайти JSON в тексті
                try:
                    # Шукаємо текст між фігурними дужками
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        result = json.loads(json_str)
                        
                        if isinstance(result, dict) and 'reviews' in result:
                            return result
                        else:
                            return {'reviews': [result]}
                            
                except (json.JSONDecodeError, ValueError):
                    pass
                
                # Якщо все невдало, повертаємо текст як відгук
                return {
                    'reviews': [{
                        'author': 'Unknown',
                        'text': response_text,
                        'rating': 0,
                        'date': None,
                        'platform_review_id': None
                    }]
                }
                
        except Exception as e:
            # Якщо є результати з прямого парсингу HTML, повертаємо їх
            if reviews:
                return {'reviews': reviews}
            raise Exception(f"Error extracting data: {str(e)}")

    def extract_review_data(self, review_html):
        """Витягує дані з HTML фрагменту відгуку"""
        try:
            # Використовуємо BeautifulSoup для базового парсингу
            soup = BeautifulSoup(review_html, 'html.parser')
            
            # Шукаємо дані за різними можливими селекторами
            author = soup.select_one('div.reviewer-name, span.author-name, div.user-name')
            rating = soup.select_one('div.rating-count, span.stars, div[data-rating]')
            date = soup.select_one('time.review-date, div.review-time, span.date')
            text = soup.select_one('div.review-text, div.comment-text, div.text')
            pros = soup.select_one('div.review-pros, div.advantages, div.plus')
            cons = soup.select_one('div.review-cons, div.disadvantages, div.minus')
            
            return {
                'author': author.text.strip() if author else None,
                'rating': float(rating['data-rating']) if rating and rating.has_attr('data-rating') else None,
                'date': date.text.strip() if date else None,
                'text': text.text.strip() if text else None,
                'advantages': pros.text.strip() if pros else None,
                'disadvantages': cons.text.strip() if cons else None
            }
        except Exception as e:
            current_app.logger.error(f"Error extracting review data: {str(e)}")
            return None

    def extract_html_blocks(self, html_content: str) -> dict:
        """Витягує потрібні HTML блоки зі сторінки"""
        soup = BeautifulSoup(html_content, 'lxml')
        blocks = {
            'title': None,
            'container': None,
            'review': None
        }

        # Шукаємо заголовок (зазвичай h1)
        title = soup.find('h1')
        if title:
            blocks['title'] = str(title)

        # Шукаємо контейнер з відгуками (типові класи)
        review_containers = soup.find_all(['div', 'section'], class_=lambda x: x and any(
            keyword in str(x).lower() 
            for keyword in ['review', 'comment', 'opinion', 'відгук', 'оценка', 'feedback']
        ))
        
        if review_containers:
            # Беремо найбільший контейнер
            container = max(review_containers, key=lambda x: len(str(x)))
            blocks['container'] = str(container)
            
            # Шукаємо один відгук всередині контейнера
            review_items = container.find_all(['div', 'article'], class_=lambda x: x and any(
                keyword in str(x).lower() 
                for keyword in ['review', 'comment', 'opinion', 'відгук', 'оценка', 'item']
            ))
            
            if review_items:
                # Беремо перший повний відгук
                blocks['review'] = str(review_items[0])

        return blocks

    def fetch_html_content(self, url: str) -> str:
        """Отримує HTML контент зі сторінки"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            current_app.logger.error(f"Помилка при отриманні HTML: {str(e)}")
            return None

    def generate_platform_config_from_url(self, url: str) -> dict:
        """Генерує конфігурацію на основі URL"""
        html_content = self.fetch_html_content(url)
        if not html_content:
            current_app.logger.error("Не вдалося отримати HTML контент")
            return {
                "parser": {
                    "config": {
                        "parser": "lxml"
                    }
                },
                "selectors": {}
            }

        # Логуємо розмір отриманого HTML
        current_app.logger.info(f"Отримано HTML розміром {len(html_content)} байт")
        
        # Витягуємо блоки
        blocks = self.extract_html_blocks(html_content)
        
        # Логуємо знайдені блоки
        for block_name, block_content in blocks.items():
            if block_content:
                current_app.logger.info(f"Знайдено блок {block_name} розміром {len(block_content)} байт")
            else:
                current_app.logger.warning(f"Блок {block_name} не знайдено")

        # Генеруємо конфігурацію
        config = self.generate_platform_config(
            url=url,
            title_selector=blocks['title'],
            review_selectors=self.analyze_review_block(blocks['review'])
        )

        if not config or not config.get('selectors'):
            current_app.logger.warning("Згенерована порожня конфігурація")
            return {
                "parser": {
                    "config": {
                        "parser": "lxml"
                    }
                },
                "selectors": {}
            }

        return config 

    def analyze_html_blocks(self, title_example: str = None, review_example: str = None) -> dict:
        """Аналізує надані приклади HTML блоків"""
        config = {
            "selectors": {
                "product": {},
                "reviews": {
                    "fields": {}
                }
            },
            "parser": {
                "config": {
                    "parser": "lxml"
                }
            }
        }

        # Аналізуємо заголовок
        if title_example:
            soup = BeautifulSoup(title_example, 'lxml')
            title_tag = soup.find('h1')
            if title_tag:
                config["selectors"]["product"]["title"] = {
                    "selector": self._get_unique_selector(title_tag),
                    "type": "text"
                }

        # Аналізуємо відгук
        if review_example:
            soup = BeautifulSoup(review_example, 'lxml')
            review_block = soup.find(attrs={"itemprop": "review"})
            
            if review_block:
                # Зберігаємо селектор для блоку відгуку
                config["selectors"]["reviews"]["item"] = f'[itemprop="review"]'
                
                # Шукаємо автора
                author = review_block.find(['span', 'div'], class_=lambda x: x and any(
                    keyword in str(x).lower() for keyword in ['author', 'user', 'name']
                ))
                if author:
                    config["selectors"]["reviews"]["fields"]["author"] = {
                        "selector": self._get_unique_selector(author),
                        "type": "text"
                    }

                # Шукаємо дату
                date = review_block.find(['time', 'span', 'div'], class_=lambda x: x and any(
                    keyword in str(x).lower() for keyword in ['date', 'time']
                ))
                if date:
                    config["selectors"]["reviews"]["fields"]["date"] = {
                        "selector": self._get_unique_selector(date),
                        "type": "text"
                    }

                # Шукаємо рейтинг
                rating = review_block.find(['div', 'span'], class_=lambda x: x and any(
                    keyword in str(x).lower() for keyword in ['rating', 'stars', 'score']
                ))
                if rating:
                    config["selectors"]["reviews"]["fields"]["rating"] = {
                        "selector": self._get_unique_selector(rating),
                        "type": "number"
                    }

                # Шукаємо текст
                text = review_block.find(['div', 'p', 'span'], class_=lambda x: x and any(
                    keyword in str(x).lower() for keyword in ['text', 'content', 'description']
                ))
                if text:
                    config["selectors"]["reviews"]["fields"]["text"] = {
                        "selector": self._get_unique_selector(text),
                        "type": "text"
                    }

        return config

    def _get_unique_selector(self, tag) -> str:
        """Створює унікальний CSS селектор для тегу"""
        if tag.get('id'):
            return f"#{tag['id']}"
            
        if tag.get('itemprop'):
            return f'[itemprop="{tag["itemprop"]}"]'
            
        if tag.get('class'):
            return f"{tag.name}.{'.'.join(tag['class'])}"
            
        # Якщо немає унікальних атрибутів, використовуємо структуру
        parents = []
        current = tag
        while current and current.name != '[document]':
            if current.get('id'):
                parents.append(f"#{current['id']}")
                break
            elif current.get('class'):
                parents.append(f"{current.name}.{'.'.join(current['class'])}")
            else:
                siblings = [s for s in current.previous_siblings if isinstance(s, Tag) and s.name == current.name]
                if siblings:
                    parents.append(f"{current.name}:nth-child({len(siblings) + 1})")
                else:
                    parents.append(current.name)
            current = current.parent
            
        return ' > '.join(reversed(parents))

    def generate_platform_config_from_examples(self, url: str, title_example: str = None, review_example: str = None) -> dict:
        """Генерує конфігурацію на основі прикладів HTML блоків"""
        try:
            prompt = f"""Проаналізуй HTML блоки та поверни конфігурацію для парсингу в форматі JSON.

            URL: {url}

            Блок з назвою товару:
            {title_example if title_example else 'Не надано'}

            Блок з відгуком:
            {review_example if review_example else 'Не надано'}

            Потрібно повернути JSON в такому форматі:
            {{
                "parser": {{
                    "type": "html",
                    "config": {{
                        "parser": "lxml"
                    }}
                }},
                "selectors": {{
                    "product": {{
                        "title": {{
                            "selector": "СЕЛЕКТОР_ЗАГОЛОВКА",
                            "type": "text"
                        }}
                    }},
                    "reviews": {{
                        "container": "СЕЛЕКТОР_КОНТЕЙНЕРА_ВІДГУКІВ",
                        "item": "СЕЛЕКТОР_ЕЛЕМЕНТА_ВІДГУКУ",
                        "fields": {{
                            "author": {{
                                "selector": "СЕЛЕКТОР_АВТОРА",
                                "type": "text"
                            }},
                            "date": {{
                                "selector": "СЕЛЕКТОР_ДАТИ",
                                "type": "text"
                            }},
                            "rating": {{
                                "selector": "СЕЛЕКТОР_РЕЙТИНГУ",
                                "type": "number"
                            }},
                            "text": {{
                                "selector": "СЕЛЕКТОР_ТЕКСТУ",
                                "type": "text"
                            }},
                            "advantages": {{
                                "selector": "СЕЛЕКТОР_ПЕРЕВАГ",
                                "type": "text"
                            }},
                            "disadvantages": {{
                                "selector": "СЕЛЕКТОР_НЕДОЛІКІВ",
                                "type": "text"
                            }}
                        }}
                    }}
                }}
            }}

            Правила:
            1. Проаналізуй HTML код та знайди всі необхідні CSS селектори
            2. Для title - знайди селектор заголовка товару
            3. Для container - знайди батьківський елемент, який містить всі відгуки
            4. Для item - знайди селектор окремого відгуку
            5. Для полів відгуку - знайди відповідні селектори всередині item
            6. Якщо якийсь селектор не знайдено - використовуй null
            7. Використовуй точні селектори з HTML
            8. Для рейтингу вкажи type: "number"
            9. Для всіх інших полів вкажи type: "text"
            
            Поверни тільки JSON без пояснень."""

            response = self._make_request_with_retry(prompt)
            if not response:
                raise Exception("Не вдалося отримати відповідь від AI")
            
            # Перевіряємо, що відповідь - валідний JSON
            config = json.loads(response)
            
            # Перевіряємо наявність всіх необхідних полів
            if not all(key in config for key in ['parser', 'selectors']):
                raise Exception("Відсутні обов'язкові поля в конфігурації")
            
            if not all(key in config['selectors'] for key in ['product', 'reviews']):
                raise Exception("Відсутні обов'язкові секції в селекторах")
            
            if not all(key in config['selectors']['reviews'] for key in ['container', 'item', 'fields']):
                raise Exception("Відсутні обов'язкові поля в секції reviews")
            
            required_fields = ['author', 'date', 'rating', 'text', 'advantages', 'disadvantages']
            if not all(field in config['selectors']['reviews']['fields'] for field in required_fields):
                raise Exception("Відсутні обов'язкові поля в конфігурації відгуків")
            
            # Замінюємо null або порожні рядки на значення за замовчуванням
            if not config['selectors']['product']['title']['selector']:
                config['selectors']['product']['title']['selector'] = 'h1'
            
            for field in required_fields:
                if not config['selectors']['reviews']['fields'][field]['selector']:
                    if field == 'advantages':
                        config['selectors']['reviews']['fields'][field]['selector'] = '.advantages, .pros, [data-test-id="plus"]'
                    elif field == 'disadvantages':
                        config['selectors']['reviews']['fields'][field]['selector'] = '.disadvantages, .cons, [data-test-id="minus"]'
                    else:
                        config['selectors']['reviews']['fields'][field]['selector'] = f'.{field}'
            
            return config
            
        except Exception as e:
            current_app.logger.error(f"Помилка при генерації конфігурації: {str(e)}")
            raise 