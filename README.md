# News Scraper

## Description

News Scraper is a Django-based web application that automatically scrapes news articles from multiple sources, providing a centralized platform for reading and exploring news content.

## Features

- **Multi-Source Scraping**: Scrape articles from different news websites (currently supports Novinky.cz and Pravda.com.ua)
- **TODO** -> **Automated Content Collection**: Periodically fetch and update articles
- **Comprehensive Article Management**:
  - Full article content and metadata
  - Image support
  - Categories and sources
- **Advanced Filtering**:
  - Filter articles by source, category, or search term
  - Pagination support
- **RESTful API**:
  - Swagger/OpenAPI documentation
  - Article filtering
- **Logging and Tracking**:
  - Detailed scraping logs
  - Track article sources and metadata

## Prerequisites

- Python 3.9+
- pip
- virtualenv (recommended)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/FoxDeFacto/WebScrapingNews.git
cd python-news-scraper
```

### 2. Create a Virtual Environment
```bash
# On Windows
python -m venv venv

# On macOS/Linux
python3 -m venv venv
```

### 3. Activate the Virtual Environment
```bash
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Database Setup
```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 6. To get data

```bash
# Register sources
python manage.py add_sources

# To reset scrapet data
python manage.py reset_db
```

### 7. Run the Development Server
```bash
python manage.py runserver
```

## Configuration

### News Sources
Configure news sources in `settings.py` under the `SCRAPER_CONFIG` section:

```python
# Scraper settings
SCRAPER_CONFIG = {
    'novinky': {
        'base_url': 'https://www.novinky.cz/',
        'categories_of_interest': [
            'Stalo se', 'Domácí', 'Volby', 'Zahraniční', 
            'Válka na Ukrajině', 'Krimi', 'Ekonomika'
        ],
    },
    'pravda': {
        'base_url': 'https://www.pravda.com.ua/',
    },
    'guardian': {
        'base_url': 'https://www.theguardian.com/europe',
        'sections_of_interest': [
            'europe',
            'technology',
            'business'
        ],
    },
}
```

### Scraping Interval
Currently only manual, but planning to add autoscraping with cron in future 

## API Usage

Access the API documentation at:
- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

### API Endpoints
- List Articles: `/api/articles/`
- Article Detail: `/api/articles/<id>/`

### Filtering Articles
Use query parameters to filter articles:
- `?title=keyword`
- `?source=novinky`
- `?category=politics`
- `?published_after=2025-01-01`

## Development

### Running Scrapers Manually
```bash
# You can create a management command to run scrapers
python manage.py run_scrapers
```

## Technologies Used

- Django
- Django REST Framework
- BeautifulSoup (Web Scraping)
- Celery (Background Tasks)
- Swagger/OpenAPI
- Tailwind CSS (Frontend)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## Autor

- Ondřej Liška ([@FoxDeFacto](https://github.com/FoxDeFacto))