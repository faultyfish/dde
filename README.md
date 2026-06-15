# DevOps & Cloud Engineer Job Board

Automated job scraping system for **DevOps, Cloud, SRE, and MLOps** roles in Ireland (Dublin + Remote).

```

## Stack

| Layer      | Tech                          |
|------------|-------------------------------|
| Scraping   | Python 3.11, Playwright       |
| Database   | Neon Postgres (serverless)    |
| API        | FastAPI + psycopg2            |
| Frontend   | Vanilla HTML/CSS/JS           |
| Hosting UI | GitHub Pages                  |
| Hosting API| Render (free tier)            |
| Automation | GitHub Actions (cron)         |

## Setup

### 1. Clone & install deps
```bash
git clone https://github.com/YOUR_USERNAME/devops-jobs-board
cd devops-jobs-board
pip install -r scraper/requirements.txt
playwright install chromium
```

### 2. Configure environment variables
Copy `.env.example` to `.env` and fill in:
```bash
cp .env.example .env
```

Required vars:
- `NEON_DATABASE_URL` — Neon Postgres connection string
- `LINKEDIN_EMAIL` — LinkedIn account email
- `LINKEDIN_PASSWORD` — LinkedIn account password

### 3. Run DB migrations
```bash
python db/migrate.py
```

### 4. Run scrapers locally
```bash
python scraper/run.py --source indeed
python scraper/run.py --source linkedin
```

### 5. Start API locally
```bash
cd api && uvicorn main:app --reload
```

## GitHub Actions Setup

Add these **Repository Secrets** (Settings → Secrets → Actions):
- `NEON_DATABASE_URL`
- `LINKEDIN_EMAIL`
- `LINKEDIN_PASSWORD`

The scraper runs automatically every day at **07:00 UTC**.

## GitHub Pages Setup

1. Go to repo **Settings → Pages**
2. Source: **Deploy from branch**
3. Branch: `main`, folder: `/ui`
4. Update `ui/config.js` with your Render API URL

## Folder Structure

```
devops-jobs-board/
├── .github/
│   └── workflows/
│       ├── scrape.yml         # Daily scraper cron
│       └── deploy-ui.yml      # Auto-deploy UI to Pages
├── scraper/
│   ├── run.py                 # Entry point
│   ├── indeed.py              # Indeed scraper
│   ├── linkedin.py            # LinkedIn scraper
│   ├── models.py              # Job data model
│   ├── utils.py               # Dedup, cleaning helpers
│   └── requirements.txt
├── db/
│   ├── schema.sql             # Table definitions
│   ├── migrate.py             # Run migrations
│   └── queries.py             # Reusable SQL helpers
├── api/
│   ├── main.py                # FastAPI app
│   ├── routes.py              # /jobs, /jobs/{id}, /stats
│   ├── db.py                  # DB connection pool
│   └── requirements.txt
├── ui/
│   ├── index.html             # Main page
│   ├── style.css              # Styles
│   ├── app.js                 # Filter + render logic
│   └── config.js              # API base URL config
├── .env.example
└── README.md
```
