from typing import Dict, Any

PROM_CONFIG = {
    "site": "prom",
    "selectors": {
        "title": {
            "selector": "h1[data-qaid='page_title']",
            "type": "text"
        },
        "reviews_container": {
            "selector": "div[data-qaid='opinion_item']",
            "type": "list"
        },
        "review": {
            "author": {
                "selector": "span[data-qaid='author_name']",
                "type": "text"
            },
            "date": {
                "selector": "time[data-qaid='date_created']",
                "type": "text"
            },
            "rating": {
                "selector": "svg[data-qaid='count_stars']",
                "attribute": "data-qaid-raiting",
                "type": "number",
                "transform": lambda x: int(x) / 20  # Конвертуємо рейтинг з 100 в 5-бальну шкалу
            },
            "title": {
                "selector": "span[data-qaid='title']",
                "type": "text"
            },
            "text": {
                "selector": "span[data-qaid='opinion_text']",
                "type": "text"
            },
            "is_verified": {
                "selector": "span[data-qaid='prom_label_text']",
                "type": "boolean",
                "transform": lambda x: "Придбано на Prom.ua" in x if x else False
            },
            "seller": {
                "selector": "span[data-qaid='company_name']",
                "type": "text",
                "transform": lambda x: x.replace("Продавець: ", "") if x else None
            },
            "images": {
                "selector": "div[data-qaid='opinion_media_block'] img",
                "attribute": "src",
                "type": "list"
            }
        }
    },
    "base_url": "https://prom.ua",
    "review_url_pattern": "/ua/product-opinions/list/{product_id}"
} 