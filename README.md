# AI Review Extractor

Сервіс для автоматичного витягування відгуків з веб-сайтів.

## Особливості

- Підтримка популярних платформ з відгуками (Google Reviews, Prom.ua, Rozetka)
- Експорт даних у CSV та JSON формати
- Система користувачів та підписок
- API для інтеграції

## Встановлення

1. Клонуйте репозиторій:
```bash
git clone https://github.com/yourusername/ai-review-extractor.git
cd ai-review-extractor
```

2. Створіть віртуальне середовище та активуйте його:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# або
venv\Scripts\activate  # для Windows
```

3. Встановіть залежності:
```bash
pip install -r requirements.txt
```

4. Встановіть Playwright:
```bash
playwright install
```

5. Створіть файл .env та налаштуйте змінні середовища:
```bash
cp .env.example .env
# Відредагуйте .env файл зі своїми налаштуваннями
```

6. Ініціалізуйте базу даних:
```bash
flask db upgrade
```

7. Запустіть сервер розробки:
```bash
flask run
```

## Структура проекту

```
ai_review_extractor/
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   └── templates/
├── migrations/
├── tests/
├── .env.example
├── .gitignore
├── config.py
├── requirements.txt
└── run.py
```

## Розробка

1. Запустіть тести:
```bash
pytest
```

2. Форматування коду:
```bash
black .
```

3. Перевірка стилю коду:
```bash
flake8
```

## Ліцензія

MIT 