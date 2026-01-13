# Project Structure

```
M01N-backend/
│
├── app/                          # Main application package
│   ├── api/                      # API routes and endpoints
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration and settings
│   │   └── database.py          # Database connection and setup
│   ├── models/                   # SQLAlchemy models
│   │   └── models.py            # Application models
│   ├── schemas/                  # Pydantic schemas
│   ├── main.py                   # FastAPI application entry point
│   ├── openai_client.py         # OpenAI integration
│   ├── supabase.py              # Supabase client
│   └── __init__.py
│
├── scrapers/                     # Web scraping scripts
│   ├── scraper.py               # Main marketplace scraper
│   ├── scraper_features.py      # Features page scraper
│   ├── requirements.txt         # Scraper dependencies
│   └── __init__.py
│
├── scripts/                      # Utility scripts
│   ├── init_db.py               # Database initialization
│   └── populate_db.py           # Database population from scraped data
│
├── data/                         # Data storage
│   └── scraped/                 # Scraped data files
│       ├── apps_encontradas.txt
│       ├── features_encontradas.txt
│       └── features_encontradas.json
│
├── docs/                         # Documentation
│   └── PROJECT_STRUCTURE.md     # This file
│
├── tests/                        # Test files
│
├── venv/                         # Virtual environment (not in git)
│
├── .env                          # Environment variables (not in git)
├── .gitignore                   # Git ignore rules
├── README.md                    # Project documentation
└── requirements.txt             # Backend dependencies
```

## Module Descriptions

### `app/`
Main FastAPI application containing all backend logic.

- **core/**: Core configuration and database setup
- **api/**: RESTful API endpoints
- **models/**: Database models (SQLAlchemy ORM)
- **schemas/**: Request/Response validation schemas (Pydantic)

### `scrapers/`
Independent web scraping scripts for bexio marketplace.

- `scraper.py`: Scrapes main app listing pages
- `scraper_features.py`: Extracts detailed features from app pages

### `scripts/`
Database management and utility scripts.

- `init_db.py`: Creates database tables
- `populate_db.py`: Imports scraped data into database

### `data/scraped/`
Output files from web scrapers (TXT, JSON formats).

## Running the Project

### Backend Server
```bash
python app/main.py
```

### Database Setup
```bash
python scripts/init_db.py
python scripts/populate_db.py
```

### Web Scrapers
```bash
python scrapers/scraper.py
python scrapers/scraper_features.py
```
