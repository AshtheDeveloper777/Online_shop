# Deployment Guide

## 1) Required Environment Variables

Set these in your deployment platform dashboard:

- `SECRET_KEY` (required)
- `DATABASE_URL` (required in production, use PostgreSQL recommended)
- `FLASK_ENV=production`
- `FLASK_DEBUG=0`
- `SUPABASE_URL` (optional)
- `SUPABASE_KEY` (optional)
- `RAZORPAY_KEY_ID` (optional)
- `RAZORPAY_KEY_SECRET` (optional)

Use `.env.example` as reference.

## 2) Install Dependencies

```bash
pip install -r requirements.txt
```

## 3) Start Command (Production)

This repo includes a `Procfile`:

```text
web: gunicorn app:app
```

If your platform needs manual command, use:

```bash
gunicorn app:app
```

## 4) Platform Notes

- **Render / Railway / Fly.io**: works directly with `Procfile`.
- **Vercel**: current `vercel.json` routes all requests to `api/index.py`.

## 5) Vercel Deployment (Flask API + React Static)

1. Push this project to GitHub.
2. In Vercel, create a new project from that repo.
3. Add environment variables in Vercel Project Settings:
   - `SECRET_KEY`
   - `DATABASE_URL` (**must be remote Postgres; do not use local sqlite file on Vercel**)
   - `FLASK_ENV=production`
   - `FLASK_DEBUG=0`
   - Optional: Supabase and Razorpay keys if features are enabled
4. Deploy.

How routing works with this repo:

- `/api/*` -> Flask serverless function (`api/index.py`)
- All other routes -> React SPA static build output

For CLI deploy:

```bash
npm i -g vercel
vercel login
vercel --prod
```

If your production domain was already deployed before this config update, redeploy to pick up the new `vercel.json`:

```bash
vercel --prod
```

## 6) Pre-Deploy Checklist

- [ ] `SECRET_KEY` is strong and not default
- [ ] `FLASK_DEBUG=0`
- [ ] Database connection (`DATABASE_URL`) is reachable
- [ ] Razorpay keys added if using live payments
- [ ] Supabase keys added if using uploads
