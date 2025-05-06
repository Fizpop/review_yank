import os
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import re
from datetime import datetime
import locale

class PlatformConfig:
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'configs', 'platforms')
        self.platforms: Dict[str, dict] = {}
        self.load_platforms()
        
    def load_platforms(self) -> None:
        """Завантажує всі конфігурації платформ з JSON файлів"""
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                platform_name = filename[:-5]  # Видаляємо .json
                filepath = os.path.join(self.config_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('enabled', True):
                        self.platforms[platform_name] = config
                        
    def detect_platform(self, url: str) -> Optional[str]:
        """Визначає платформу на основі URL"""
        domain = urlparse(url).netloc.lower()
        
        # Спочатку перевіряємо точне співпадіння домену
        for platform_name, config in self.platforms.items():
            if domain == config.get('domain', '').lower():
                return platform_name
                
        # Потім перевіряємо піддомени
        for platform_name, config in self.platforms.items():
            domains = config.get('domains', [])
            if isinstance(domains, list):
                for d in domains:
                    if domain.endswith(d.lower()):
                        return platform_name
                        
        return None
        
    def get_selector(self, platform: str, selector_path: str) -> Optional[dict]:
        """Отримує селектор за його шляхом в конфігурації"""
        if platform not in self.platforms:
            return None
            
        config = self.platforms[platform]
        parts = selector_path.split('.')
        
        current = config
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return None
                
        return current
        
    def transform_value(self, platform: str, value: str, transformer_name: str) -> Any:
        """Застосовує трансформацію до значення"""
        if platform not in self.platforms:
            return value
            
        config = self.platforms[platform]
        if 'transformers' not in config or transformer_name not in config['transformers']:
            return value
            
        transformer = config['transformers'][transformer_name]
        
        if transformer['type'] == 'regex':
            pattern = transformer['pattern']
            transform_func = eval(transformer['transform'])
            match = re.search(pattern, value)
            if match:
                return transform_func(match.groups())
                
        elif transformer['type'] == 'date':
            try:
                locale.setlocale(locale.LC_TIME, transformer['locale'])
                return datetime.strptime(value, transformer['format'])
            except (ValueError, locale.Error):
                return None
                
        return value
        
    def get_error_solution(self, platform: str, error_message: str) -> Optional[str]:
        """Знаходить рішення для помилки на основі шаблонів"""
        if platform not in self.platforms:
            return None
            
        config = self.platforms[platform]
        if 'error_patterns' not in config:
            return None
            
        for pattern in config['error_patterns']:
            if re.search(pattern['pattern'], error_message):
                return pattern['solution']
                
        return None
        
    def validate_review(self, platform: str, review: dict) -> List[str]:
        """Перевіряє валідність відгуку"""
        errors = []
        
        if platform not in self.platforms:
            return ['Unknown platform']
            
        config = self.platforms[platform]
        validation = config.get('validation', {})
        
        # Перевіряємо обов'язкові поля
        for field in validation.get('required_fields', []):
            if not review.get(field):
                errors.append(f"Missing required field: {field}")
                
        # Перевіряємо рейтинг
        if 'rating' in review:
            try:
                rating = float(review['rating'])
                if rating < validation.get('min_rating', 1) or rating > validation.get('max_rating', 5):
                    errors.append(f"Rating out of range: {rating}")
            except (ValueError, TypeError):
                errors.append("Invalid rating format")
                
        return errors
        
    def save_platform_config(self, platform: str, config: dict) -> bool:
        """Зберігає оновлену конфігурацію платформи"""
        if not platform:
            return False
            
        filepath = os.path.join(self.config_dir, f"{platform}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.platforms[platform] = config
            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False 