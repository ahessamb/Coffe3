## Docker startup (Coffe3)

### Prerequisite
- Install **Docker Desktop** and make sure Docker is **running**.

---

### Option A) Run locally (recommended)
In the project root:

```bash
docker compose up --build
```

Open `http://localhost:8000`

Stop:

```bash
Ctrl+C
```

Remove containers (keeps volumes/data unless you add `-v`):

```bash
docker compose down
```

---

### Option B) Build a portable image (share it)
Build the image:

```bash
docker build -t coffe3:latest .
```

Export to a single file:

```bash
docker save -o coffe3_latest.tar coffe3:latest
```

On another machine, import it:

```bash
docker load -i coffe3_latest.tar
```

---

### Run the exported image (without Compose)
Run:

```bash
docker run --rm -p 8000:8000 coffe3:latest
```

Open `http://localhost:8000`
