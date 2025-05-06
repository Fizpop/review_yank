from bs4 import BeautifulSoup
from app.services.base_extractor import BaseExtractor
from app.config.selectors import ROZETKA_SELECTORS

class RozetkaExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.selectors = ROZETKA_SELECTORS

    def extract_reviews(self, html: str) -> list:
        soup = BeautifulSoup(html, 'html.parser')
        reviews = []
        
        review_containers = soup.select(self.selectors['review_container'])
        
        for container in review_containers:
            try:
                author = container.select_one(self.selectors['author']).text.strip()
                date = container.select_one(self.selectors['date']).text.strip()
                rating = self._extract_rating(container)
                text = container.select_one(self.selectors['text']).text.strip()
                product_info = container.select_one(self.selectors['product_info']).text.strip()
                
                advantages = container.select_one(self.selectors['advantages'])
                advantages = advantages.text.strip() if advantages else None
                
                disadvantages = container.select_one(self.selectors['disadvantages'])
                disadvantages = disadvantages.text.strip() if disadvantages else None
                
                review = {
                    'author': author,
                    'date': date,
                    'rating': rating,
                    'text': text,
                    'product_info': product_info,
                    'advantages': advantages,
                    'disadvantages': disadvantages
                }
                
                reviews.append(review)
                
            except Exception as e:
                print(f"Error extracting review: {str(e)}")
                continue
                
        return reviews
        
    def _extract_rating(self, container) -> float:
        rating_element = container.select_one(self.selectors['rating'])
        if not rating_element:
            return None
            
        # Рейтинг представлений як ширина елемента в процентах
        style = rating_element.get('style', '')
        if 'width:' in style:
            width = style.split('width:')[1].split('%')[0].strip()
            try:
                return float(width) / 20  # Конвертуємо відсотки в рейтинг 1-5
            except:
                return None
        return None 