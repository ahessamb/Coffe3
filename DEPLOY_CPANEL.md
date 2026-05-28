# Deploy Coffe3 (Django + Wagtail) on cPanel shared hosting

This guide assumes **no SSH** — only [cPanel](http://zhinadcoffee.ir:2083) and **cPanel Terminal**.

Your repo: https://github.com/ahessamb/Coffe3  
Application folder on server: `~/Coffe3/zhinadproject` (contains `manage.py` and `passenger_wsgi.py`).

---

## What you are building (mental model)

```
Browser → domain (zhinadcoffee.ir / zhinad.ir)
       → cPanel "Python App" (Passenger)
       → passenger_wsgi.py → Django
       → MySQL (recommended) or SQLite (test only)
```

Static CSS/JS: collected into `staticfiles/` and served by **WhiteNoise**.  
Uploaded images: `media/` (served by Django when `DJANGO_SERVE_MEDIA=1`).

---

## Phase 0 — Before you touch Python

### 0.1 Log in to cPanel

Open: http://zhinadcoffee.ir:2083

### 0.2 Back up the current static site

1. **File Manager** → `public_html`
2. Select `index.html` (and any other site files) → **Compress** → download the zip, or move them to a folder `public_html_old_static`

You will stop using these files once the Python app owns the domain.

### 0.3 Check Python is available

1. cPanel search: **Setup Python App** (or **Python App** / **Application Manager**)
2. If you do not see it, ask your host to enable **Python Selector / Passenger**. Without this, Django cannot run on shared hosting.

Note the highest Python version offered (3.10 or 3.11 is ideal).

---

## Phase 1 — MySQL database (recommended)

SQLite works for a quick test but is fragile on shared hosting (locking, backups). Use MySQL for production.

1. cPanel → **MySQL Databases**
2. **Create database**, e.g. `zhinad_db` → full name will be like `cpuser_zhinad_db`
3. **Create user** with a strong password
4. **Add user to database** → **ALL PRIVILEGES**
5. Write down these four values (you need them later):

| Label | Example |
|--------|---------|
| DB name | `cpuser_zhinad_db` |
| DB user | `cpuser_zhinad` |
| DB password | *(your password)* |
| DB host | `localhost` |

---

## Phase 2 — Clone the project

### Option A — cPanel Git (if available)

1. **Git Version Control** → **Create**
2. Clone URL: `https://github.com/ahessamb/Coffe3.git`
3. Repository path: `/home/YOUR_CPANEL_USER/Coffe3`
4. Clone

### Option B — Terminal in cPanel

1. **Terminal**
2. Run:

```bash
cd ~
git clone https://github.com/ahessamb/Coffe3.git
cd Coffe3
ls
```

You should see `requirements.txt` and `zhinadproject/manage.py`.

---

## Phase 3 — Create the Python application

1. **Setup Python App** → **Create Application**

| Field | Value |
|--------|--------|
| Python version | Highest available (3.10+) |
| Application root | `/home/YOUR_USER/Coffe3/zhinadproject` |
| Application URL | `/` on **zhinadcoffee.ir** (primary domain) |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

2. Click **Create**.

cPanel creates a virtualenv and may write its own `passenger_wsgi.py`.  
**Important:** After the first deploy, open `~/Coffe3/zhinadproject/passenger_wsgi.py` in File Manager and confirm it matches the repo version (imports `zhinadproject.settings`). If cPanel overwrote it with a stub, paste the content from GitHub.

3. On the same Python App page, find **Configuration files** / **Environment variables** and add:

| Variable | Value |
|----------|--------|
| `DJANGO_SECRET_KEY` | Long random string (50+ chars). Generate locally: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `0` |
| `WAGTAILADMIN_BASE_URL` | `https://zhinadcoffee.ir` |
| `DB_ENGINE` | `django.db.backends.mysql` |
| `DB_NAME` | *(full MySQL database name)* |
| `DB_USER` | *(MySQL user)* |
| `DB_PASSWORD` | *(MySQL password)* |
| `DB_HOST` | `localhost` |
| `DB_PORT` | `3306` |
| `DJANGO_SERVE_MEDIA` | `1` |
| `DJANGO_SECURE_PROXY` | `1` |
| `DJANGO_SESSION_COOKIE_SECURE` | `1` |
| `DJANGO_CSRF_COOKIE_SECURE` | `1` |

(See `.env.example` in the repo.)

4. **Save** and note the **virtualenv activation command** shown on the page, e.g.:

```bash
source /home/USER/virtualenv/Coffe3/zhinadproject/3.11/bin/activate
```

Paths vary by host — always copy from **your** cPanel screen.

---

## Phase 4 — Install dependencies and prepare Django

Open **Terminal**, then run (adjust the `source` line to match your panel):

```bash
cd ~/Coffe3
source /home/YOUR_USER/virtualenv/Coffe3/zhinadproject/3.11/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd zhinadproject
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

- `migrate` — creates tables in MySQL  
- `collectstatic` — fills `staticfiles/` for WhiteNoise  
- `createsuperuser` — login for `/admin/` and Wagtail `/cms/`

If `pip install` fails on `Pillow` or `PyMySQL`, use **Setup Python App** → **Run Pip Install** with `requirements.txt` path `/home/YOUR_USER/Coffe3/requirements.txt`, then retry in Terminal.

---

## Phase 5 — Point domains to the app

### Primary domain (zhinadcoffee.ir)

Creating the Python app with Application URL `/` usually sets the document root to `~/Coffe3/zhinadproject`.  
Verify:

1. **Domains** → **Domains** (or **Addon Domains**)
2. `zhinadcoffee.ir` → **Document Root** should be something like:

   `/home/YOUR_USER/Coffe3/zhinadproject`

   **Not** `public_html` if you want Django on the homepage.

### Second domain (zhinad.ir)

Both domains should use the **same document root** as the Python app:

1. **Domains** → edit `zhinad.ir`
2. Set **Document Root** to the **same path** as `zhinadcoffee.ir` (`~/Coffe3/zhinadproject`)
3. Save

If cPanel will not share a document root between domains, set `zhinad.ir` as a **redirect** to `https://zhinadcoffee.ir` (Domains → Redirects).

---

## Phase 6 — SSL (HTTPS)

1. **SSL/TLS Status** or **Let's Encrypt**
2. Issue certificates for `zhinadcoffee.ir`, `www.zhinadcoffee.ir`, `zhinad.ir`, `www.zhinad.ir`
3. Turn on **Force HTTPS Redirect** if available

Ensure `WAGTAILADMIN_BASE_URL` uses `https://`.

---

## Phase 7 — Restart the app

After any code or env change:

1. **Setup Python App** → your app → **Restart**
2. Or Terminal:

```bash
mkdir -p ~/Coffe3/zhinadproject/tmp
touch ~/Coffe3/zhinadproject/tmp/restart.txt
```

---

## Phase 8 — Wagtail site hostname (required once)

1. Visit `https://zhinadcoffee.ir/admin/` — log in with superuser
2. Visit `https://zhinadcoffee.ir/cms/`
3. **Settings** → **Sites** → edit the default site
4. Set **Hostname** to `zhinadcoffee.ir` (no `https://`, no trailing slash)
5. **Port** `443` if there is a port field and you use HTTPS
6. Save

---

## Phase 9 — Verify

| URL | Expected |
|-----|----------|
| `https://zhinadcoffee.ir/` | Shop / home page |
| `https://zhinadcoffee.ir/admin/` | Django admin |
| `https://zhinadcoffee.ir/cms/` | Wagtail CMS |
| `https://zhinad.ir/` | Same site (if document root shared) |

---

## Updating after you push to GitHub

Terminal:

```bash
cd ~/Coffe3
git pull
source /home/YOUR_USER/virtualenv/Coffe3/zhinadproject/3.11/bin/activate
pip install -r requirements.txt
cd zhinadproject
python manage.py migrate
python manage.py collectstatic --noinput
touch tmp/restart.txt
```

Then **Restart** the Python app in cPanel.

---

## Troubleshooting

### 500 Internal Server Error

1. **Setup Python App** → **passenger.log** or **error log** (if shown)
2. File Manager → `~/Coffe3/zhinadproject/logs/django.log`
3. Common causes:
   - Wrong `Application root` (must be folder with `manage.py`)
   - `DJANGO_DEBUG=0` but missing `DJANGO_SECRET_KEY` or DB credentials
   - Forgot `migrate` or `collectstatic`
   - `ALLOWED_HOSTS` — add host in env: `DJANGO_ALLOWED_HOSTS=zhinad.ir,zhinadcoffee.ir`

Temporarily set `DJANGO_DEBUG=1`, restart, reproduce error, read traceback, then set back to `0`.

### Static files broken (no CSS)

```bash
cd ~/Coffe3/zhinadproject
python manage.py collectstatic --noinput
touch tmp/restart.txt
```

### Images 404

- Confirm `media/` exists under `zhinadproject/` (clone includes sample media)
- Confirm `DJANGO_SERVE_MEDIA=1`
- New uploads go to `zhinadproject/media/` — ensure folder is writable (chmod 755/775 via File Manager)

### Still see old static HTML

- Document root still `public_html` → change to `zhinadproject` folder
- Browser cache — hard refresh or private window
- Old `index.html` in `public_html` is ignored only if document root moved

### CSRF errors on login/forms

Add to environment variables:

```
DJANGO_CSRF_TRUSTED_ORIGINS=https://zhinadcoffee.ir,https://www.zhinadcoffee.ir,https://zhinad.ir,https://www.zhinad.ir
```

### "DisallowedHost"

Add the exact hostname to `DJANGO_ALLOWED_HOSTS` (comma-separated, no spaces).

---

## Security checklist

- [ ] `DJANGO_DEBUG=0` in production
- [ ] Strong `DJANGO_SECRET_KEY` (never commit real key to GitHub)
- [ ] MySQL user only for this database
- [ ] HTTPS enabled
- [ ] Superuser password stored safely

---

## Quick reference — folder layout on server

```
/home/YOUR_USER/
  Coffe3/                          ← git clone root
    requirements.txt
    zhinadproject/                 ← Python Application root
      manage.py
      passenger_wsgi.py
      db.sqlite3                   ← only if NOT using MySQL
      staticfiles/                 ← after collectstatic
      media/
      logs/django.log
```
