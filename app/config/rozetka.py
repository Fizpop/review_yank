ROZETKA_CONFIG = {
    'name': 'rozetka',
    'base_url': 'https://rozetka.com.ua',
    'selectors': {
        'product_title': 'h1.product__title',
        'review_item': '.product-comments__list-item',
        'review_fields': {
            'author': '[data-testid="replay-header-author"]',
            'date': '[data-testid="replay-header-date"]',
            'rating': '.stars__rating',
            'text': '.comment__body-wrapper p',
            'advantages': '.comment__essentials dd',
            'disadvantages': '.comment__essentials dd:nth-of-type(2)'
        }
    }
} 