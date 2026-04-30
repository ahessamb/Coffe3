## Coffe3 startup

### Run locally
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`
- `python zhinadproject/manage.py migrate`
- `python zhinadproject/manage.py runserver`

### Run with Docker
- `docker compose up --build`
- Open `http://localhost:8000`
