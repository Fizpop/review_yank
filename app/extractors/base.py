from typing import Dict, Any, List
from abc import ABC, abstractmethod
import logging
from app.services.browser_fetcher import fetch_html_with_js

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def get_html(self, url: str) -> str:
        """Get HTML content from URL using Playwright."""
        logger.info(f"Отримуємо HTML для URL: {url}")
        try:
            html = fetch_html_with_js(url)
            logger.debug("HTML успішно отримано")
            return html
        except Exception as e:
            logger.error(f"Помилка при отриманні HTML: {str(e)}")
            raise
    
    @abstractmethod
    def extract_reviews(self, html: str) -> List[Dict[str, Any]]:
        """Extract reviews from HTML."""
        pass
    
    @abstractmethod
    def extract_product_info(self, html: str) -> Dict[str, Any]:
        """Extract product information from HTML."""
        pass
    
    @abstractmethod
    def get_product_id_from_url(self, url: str) -> str:
        """Extract product ID from URL."""
        pass 