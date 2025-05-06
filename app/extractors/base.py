from typing import Dict, Any, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
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