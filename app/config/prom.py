PROM_CONFIG = {
    'parser': 'lxml',
    'domains': ['prom.ua'],
    'selectors': {
        'product_title': 'h1[data-qaid="page_title"]',
        'reviews_container': 'div[data-qaid="comments_list"]',
        'review_item': 'div[data-qaid="opinion_item"]',
        'review_fields': {
            'author': 'span[data-qaid="author_name"]',
            'title': 'span[data-qaid="title"]',
            'text': 'div[data-qaid="opinion_text"]',
            'rating': 'svg[data-qaid="count_stars"]',
            'date': 'time[data-qaid="date_created"]',
            'verified_purchase': 'span[data-qaid="prom_label_text"]'
        }
    }
}