# AttendX — Deployment Guide

## Prerequisites
- Supabase account (free tier)
- Render.com account (free tier)
- GitHub account (for Pages)

---

## Step 1: Supabase Database Setup

1. Go to https://supabase.com → New Project
2. Note your **Project URL** and **anon/service key**
3. Open the SQL Editor and paste the contents of `backend/schema.sql`
4. Run to create all tables and enums
5. Go to **Settings → API** and copy the `DATABASE_URL` (connection string)
6. Enable the **pgvector** extension via: `CREATE EXTENSION IF NOT EXISTS vector;`

---

## Step 2: Generate the Default Admin Password Hash

Run locally:
```bash
cd attendX/backend
python -c "import bcrypt; print(bcrypt.hashpw(b'Admin@1234', bcrypt.gensalt()).decode())"
```
Copy the output hash and update the last line of `schema.sql` before running it in Supabase.

---

## Step 3: Deploy Backend to Render

1. Push the `attendX/backend/` folder to a GitHub repository
2. Go to https://render.com → New Web Service
3. Connect your GitHub repo
4. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add Environment Variables:
   - `DATABASE_URL` → your Supabase connection string
   - `JWT_SECRET_KEY` → a long random string
   - `FRONTEND_URL` → your GitHub Pages URL (e.g. `https://yourusername.github.io/attendX`)
   - `FLASK_ENV` → `production`
6. Deploy. Note the Render URL (e.g. `https://attendx-api.onrender.com`)

---

## Step 4: Update Frontend API URL

In `attendX/frontend/js/utils.js`, update:
```js
const API_BASE = "https://your-actual-render-url.onrender.com/api";
```

---

## Step 5: Deploy Frontend to GitHub Pages

1. Push `attendX/frontend/` to a GitHub repo (can be same or separate)
2. Go to **Settings → Pages**
3. Source: **Deploy from branch → main → / (root)**
4. Your site will be live at `https://yourusername.github.io/attendX/`

---

## Step 6: First Login

Navigate to your GitHub Pages URL. Use:
- **Email**: `admin@university.edu`
- **Password**: `password` (change immediately after first login)
