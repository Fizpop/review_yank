ROZETKA_CONFIG = {
    'parser': 'lxml',
    'domains': ['rozetka.com.ua', 'bt.rozetka.com.ua'],
    'selectors': {
        'product_title': "h1.product__title",
        'reviews_container': "div.product-comments",
        'review_item': "div.comment__inner",
        'review_fields': {
            'author': "div[data-testid='replay-header-author']",
            'date': "time[data-testid='replay-header-date']",
            'rating': "div[data-testid='stars-rating']",
            'text': "div.comment__body",
            'advantages': "div.comment__advantages",
            'disadvantages': "div.comment__disadvantages"
        }
    }
} 