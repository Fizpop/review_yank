from typing import Optional
from app.extractors.base import BaseExtractor
from app.extractors.prom import PromExtractor
from app.extractors.rozetka import RozetkaExtractor

class ExtractorFactory:
    @staticmethod
    def create_extractor(platform: str) -> Optional[BaseExtractor]:
        """Створює екстрактор для вказаної платформи"""
        extractors = {
            'prom': PromExtractor,
            'rozetka': RozetkaExtractor
        }
        
        extractor_class = extractors.get(platform.lower())
        if extractor_class:
            return extractor_class()
        return None 