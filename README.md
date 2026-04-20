# Ultimate AI Commerce (Flask + React)

Production-style e-commerce app with:

- Flask backend (`/api/...`) for auth, products, cart, checkout, orders
- React + Vite frontend served by Flask at [`/app`](http://127.0.0.1:5000/app)
- SQLite by default, PostgreSQL supported via `DATABASE_URL`
- Session auth via Flask-Login, secure password hashing
- Existing template pages still available (legacy routes)

## Quick Start

1. **Backend setup**

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. **Frontend setup/build**

```bash
cd frontend
npm install
npm run build
cd ..
```

If you want Flask to serve the same build at `/app` locally:

```bash
cd frontend
$env:VITE_BASE_PATH="/app/"
npm run build
cd ..
```

3. **Run app**

```bash
.venv\Scripts\python.exe app.py
```

Then open:

- `http://127.0.0.1:5000/app` (React storefront)
- `http://127.0.0.1:5000` (legacy Flask templates)

## Frontend Dev Mode

In one terminal:

```bash
.venv\Scripts\python.exe app.py
```

In another terminal:

```bash
cd frontend
npm run dev
```

Vite proxies `/api` to Flask, so the React app works in local dev with real backend data.

## Environment Variables

Use `.env`:

- `SECRET_KEY`
- `DATABASE_URL`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `SUPABASE_URL`
- `SUPABASE_KEY`

## Vercel Notes

- Vercel uses `vercel.json` to deploy:
  - React static site at root (`/`)
  - Flask API on `/api/*`
- Ensure `DATABASE_URL` points to a remote production database.