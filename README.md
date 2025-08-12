# JP Ford SKU Generator

4-character SKU generator using a safe 32-character alphabet (0-9, A-Z without B, I, O, S). Guarantees uniqueness using an atomic SQLite counter. Web UI + Flask API.

## Character Set
```
0123456789ACDEFGHJKLMNPRTUVWXYZ
```
Total combinations: 32^4 = 1,048,576.

## Run Locally
```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# visit http://localhost:5000
```

## Deploy on Render (Free)
1. Create a **new GitHub repo** and upload these files.
2. Go to **Render.com → New → Blueprint**.
3. Select your repo (it will detect `render.yaml`).
4. Click **Deploy**. Render provisions a free web service with a public URL.
5. Wait for build to finish, then open the URL.
6. (First request may be a cold start after long idle — normal on free plans.)

### Notes
- The app stores a SQLite database `sku.db` in the service disk. On Render free plans, the disk persists across deploys and restarts as long as you keep the same instance.
- Health check: `GET /healthz` returns `ok` when the app is running.
- API: `POST /api/next` returns `{ "sku": "XXXX" }`.

## Concurrency
The counter increment is wrapped in `BEGIN IMMEDIATE` (SQLite), ensuring only one client increments at a time.

## Exhaustion
If more than 1,048,576 SKUs are generated, the API returns an error. Increase to 5 or more characters to expand the space.
