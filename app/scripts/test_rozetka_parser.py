from app import create_app
from app.extractors.rozetka import RozetkaExtractor
import json

def test_rozetka_parser():
    """Test Rozetka reviews parser"""
    app = create_app()
    
    with app.app_context():
        try:
            # Створюємо екстрактор
            extractor = RozetkaExtractor()
            
            # URL для тестування
            url = "https://rozetka.com.ua/ua/weestep_roz6400165514/p336792325/comments/"
            
            print(f"\nТестуємо парсинг відгуків з URL: {url}")
            
            # Отримуємо HTML через Playwright
            html = extractor.get_html(url)
            print("HTML успішно отримано")
            
            # Зберігаємо HTML для аналізу
            with open("rozetka_test.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("\nHTML збережено у файл rozetka_test.html")
            
            # Витягуємо відгуки
            reviews = extractor.extract_reviews(html)
            print(f"\nЗнайдено відгуків: {len(reviews)}")
            
            # Виводимо результати
            print("\nРезультати парсингу:")
            for i, review in enumerate(reviews, 1):
                print(f"\nВідгук #{i}:")
                print(json.dumps(review, ensure_ascii=False, indent=2))
                
        except Exception as e:
            print(f"Помилка при тестуванні: {str(e)}")

if __name__ == "__main__":
    test_rozetka_parser() 