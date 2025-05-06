from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import time
import json
from datetime import datetime

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

def save_and_analyze_rozetka():
    with sync_playwright() as p:
        # Запускаємо браузер
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Відкриваємо сторінку
        url = "https://rozetka.com.ua/ua/weestep_roz6400165514/p336792325/comments/"
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
        
        # Зберігаємо HTML
        with open('rozetka_test.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('HTML збережено у файл rozetka_test.html')
        
        # Аналізуємо відгуки
        soup = BeautifulSoup(html, 'html.parser')
        reviews = soup.select('.product-comments__list-item')
        print(f'\nЗнайдено відгуків: {len(reviews)}')
        
        # Збираємо дані про всі відгуки
        all_reviews = []
        for i, review in enumerate(reviews, 1):
            print(f'\nОбробка відгуку #{i}:')
            print(f'HTML відгуку:\n{review.prettify()}\n')
            
            review_data = extract_review_data(review)
            all_reviews.append(review_data)
            
            # Виводимо знайдені дані
            print(f'Знайдені дані:')
            for key, value in review_data.items():
                if value:  # Виводимо тільки непусті значення
                    print(f'{key}: {value}')
            print('-' * 50)
        
        # Зберігаємо результати в JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'rozetka_reviews_{timestamp}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'url': url,
                'total_reviews': len(all_reviews),
                'parsed_at': datetime.now().isoformat(),
                'reviews': all_reviews
            }, f, ensure_ascii=False, indent=2)
        
        print(f'\nРезультати збережено у файл {output_file}')
        
        # Виводимо статистику
        ratings = [r['rating'] for r in all_reviews if r['rating'] is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            print(f'\nСтатистика:')
            print(f'Середній рейтинг: {avg_rating:.1f}')
            print(f'Кількість відгуків з рейтингом: {len(ratings)}')
            print(f'Кількість відгуків без рейтингу: {len(all_reviews) - len(ratings)}')
        
        # Закриваємо браузер
        browser.close()

if __name__ == '__main__':
    save_and_analyze_rozetka() 