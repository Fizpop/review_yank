import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def extract_prom_reviews(url):
    """
    Тестовий парсер для відгуків з Prom.ua
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    reviews = []
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Знаходимо всі відгуки за стабільним data-qaid
        review_items = soup.find_all('div', attrs={'data-qaid': 'opinion_item'})
        
        print(f"Знайдено відгуків: {len(review_items)}")
        
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
                review['review_id'] = item['data-qaopinionid']
            
            reviews.append(review)
            print(f"Оброблено відгук: {json.dumps(review, ensure_ascii=False, indent=2)}")
            
        return reviews
        
    except Exception as e:
        print(f"Помилка при парсингу: {str(e)}")
        return []

if __name__ == "__main__":
    test_url = "https://prom.ua/ua/product-opinions/list/2213108425"
    print(f"Починаємо парсинг відгуків з {test_url}")
    
    reviews = extract_prom_reviews(test_url)
    
    print("\nРезультати парсингу:")
    print(f"Всього оброблено відгуків: {len(reviews)}")
    
    # Зберігаємо результати в JSON файл
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"prom_reviews_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
    
    print(f"Результати збережено у файл: {output_file}") 