from typing import Dict, Any

ADMIN_CONFIG: Dict[str, Any] = {
    "platforms": [
        {
            "id": "prom",
            "name": "Prom.ua",
            "domain": "prom.ua",
            "config": {
                "selectors": {
                    "reviews": {
                        "container": "div[data-qaid='opinion_list']",
                        "item": "div[data-qaid='opinion_item']",
                        "fields": {
                            "author": {
                                "selector": "span[data-qaid='author_name']",
                                "attribute": "text",
                                "type": "text"
                            },
                            "date": {
                                "selector": "time[data-qaid='date_created']",
                                "attribute": "text",
                                "type": "text"
                            },
                            "rating": {
                                "selector": "svg[data-qaid='count_stars']",
                                "attribute": "data-qaid-raiting",
                                "type": "number",
                                "converter": "divide_by_20"
                            },
                            "text": {
                                "selector": "span[data-qaid='title']",
                                "attribute": "text",
                                "type": "text"
                            },
                            "verified_purchase": {
                                "selector": "span[data-qaid='prom_label_text']",
                                "type": "boolean",
                                "exists": true
                            },
                            "platform_review_id": {
                                "selector": "div[data-qaid='opinion_item']",
                                "attribute": "data-qaopinionid",
                                "type": "text"
                            }
                        }
                    },
                    "product": {
                        "title": {
                            "selector": "h1[data-qaid='product_name']",
                            "attribute": "text",
                            "type": "text"
                        }
                    }
                },
                "url_patterns": {
                    "product": "https://prom.ua/ua/p{product_id}",
                    "reviews": "https://prom.ua/ua/product-opinions/list/{product_id}"
                },
                "parser": {
                    "type": "beautifulsoup",
                    "config": {
                        "parser": "lxml",
                        "attrs_mode": true
                    }
                }
            }
        },
        {
            "id": "rozetka",
            "name": "Rozetka",
            "domain": "rozetka.com.ua",
            "config": {
                "selectors": {
                    "reviews": {
                        "container": "ul.product-reviews",
                        "item": "li.product-review",
                        "fields": {
                            "author": {"selector": ".review-author"},
                            "date": {"selector": ".review-date"},
                            "rating": {"selector": ".rating-value", "attribute": "data-rating"},
                            "text": {"selector": ".review-text"}
                        }
                    },
                    "product": {
                        "name": {"selector": "h1.product__title"}
                    }
                },
                "url_patterns": {
                    "product": "https://rozetka.com.ua/ua/{product_id}/p{product_id}/",
                    "reviews": "https://rozetka.com.ua/ua/{product_id}/comments/"
                }
            }
        }
    ],
    "ui": {
        "platform_form": {
            "fields": [
                {"name": "name", "type": "text", "label": "Назва"},
                {"name": "domain", "type": "text", "label": "Домен"},
                {"name": "config", "type": "json", "label": "Конфігурація (JSON)"}
            ]
        }
    }
} 