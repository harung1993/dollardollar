# Contributing to DollarDollar

## Development Setup
1. Clone the repo: `git clone https://github.com/harung1993/dollardollar.git`
2. Copy environment: `cp .env.template .env`
3. Start with Docker: `docker-compose up -d`
4. Access at: `http://localhost:5006`

## Database Updates
After pulling updates, run:
```bash
flask db migrate
flask db upgrade
