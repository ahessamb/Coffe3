## Deploy to IranHost (cPanel) for `zhinadcoffee.ir`

### 0) One-time: make sure your repo is clean
cPanel Git deploy refuses if the checked-out branch has local changes.

- Make sure you **commit + push** these changes from your laptop:
  - Added `.cpanel.yml`, `.gitignore`, `passenger_wsgi.py`
  - Removed tracked `__pycache__/*.pyc` from git

---

### 1) Create the Python app in cPanel
In cPanel:
- Go to **Setup Python App**
- Create an app:
  - **Python**: 3.x (whatever IranHost provides)
  - **Application root**: `zhinad_app`
  - **Application URL**: choose the domain `zhinadcoffee.ir` (or the subdomain you want)
  - **Application startup file**: `passenger_wsgi.py`
  - **Application entry point**: `application`

This creates a Passenger-based Python app.

---

### 2) Set environment variables in cPanel
In the Python app settings, add:
- `DJANGO_DEBUG=0`
- `DJANGO_SECRET_KEY=<a long random secret>`

Optional (recommended later):
- `DJANGO_SETTINGS_MODULE=zhinadproject.settings` (usually not needed because `passenger_wsgi.py` sets it)

---

### 3) Connect Git repo + enable “Deploy”
In cPanel:
- Go to **Git Version Control**
- Add/Manage your repository
- Ensure the repository contains a valid `.cpanel.yml` at the root

When you click **Deploy**, cPanel will:
- Sync repo → `$HOME/zhinad_app`
- Create/update venv in `$HOME/zhinad_app/venv`
- `pip install -r requirements.txt`
- Run `migrate` and `collectstatic`
- Touch `tmp/restart.txt` to reload Passenger

---

### 4) After deploy: verify
Visit:
- `https://zhinadcoffee.ir/` (home)
- `https://zhinadcoffee.ir/admin/` (Django admin)

If admin doesn’t load, check:
- cPanel **Errors** / **Application logs**
- That `DJANGO_DEBUG=0` is set
- That dependencies installed correctly

---

### Notes / common gotchas
- **SQLite**: this project uses SQLite by default. On shared hosting that’s OK for small sites.
- **Static files**: `collectstatic` writes to `zhinadproject/staticfiles/` (kept on the host).
- **Media uploads**: uploaded files go to `zhinadproject/media/` (kept on the host).
