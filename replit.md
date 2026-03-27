# KaziX — Hire Trusted Fundis in Kenya

## Overview
KaziX is a modern marketplace connecting skilled Kenyan workers (fundis) with clients. The platform features M-Pesa escrow payments, ID verification, and a transparent review system.

## Architecture

### Frontend
- **Type:** Static HTML5 / Vanilla CSS3 / JavaScript
- **Location:** `frontend/`
  - `frontend/pages/` — All HTML pages (index, dashboards, admin, etc.)
  - `frontend/assets/css/` — Stylesheets (styles.css, admin.css)
  - `frontend/assets/js/` — JavaScript files (mobile-nav.js, admin-shell.js, admin-disputes.js)
- **Served by:** `serve.js` (Node.js custom static file server)
- **Port:** 5000 (webview)
- **Design:** High-contrast "Modern Brutalist" aesthetic
- **Fonts:** Syne (headings), DM Sans (body)

### Backend — FastAPI (Primary)
- **Location:** `backend/app/`
- **Framework:** FastAPI + Uvicorn
- **Port:** 8000 (console workflow)
- **Database:** Supabase (PostgreSQL)
- **Auth:** Supabase Phone OTP
- **Payments:** M-Pesa Daraja API (STK Push + Escrow)
- **SMS:** Africa's Talking

#### API Routes (v1)
- `POST /v1/auth/send-otp` — Send phone OTP
- `POST /v1/auth/verify-otp` — Verify OTP & get session
- `POST /v1/auth/profile` — Complete registration
- `GET  /v1/auth/session` — Get current user + profile
- `/v1/profiles` — Worker/client profiles
- `/v1/jobs` — Job postings
- `/v1/applications` — Job applications
- `/v1/bookings` — Bookings management
- `/v1/mpesa` — M-Pesa payment flows
- `/v1/admin` — Admin endpoints
- `GET /health` — Health probe
- `GET /docs` — Swagger UI (dev only)

### Backend — Node.js/Express (Scaffolding)
- **Location:** `backend/` (server.js + routes/)
- **Status:** Placeholder routes only (not actively used)

## Workflows
- **Start application** — `node serve.js` on port 5000 (frontend webview)
- **Backend API** — `uvicorn app.main:app` on port 8000 (console)

## Environment Variables
These must be set in Replit Secrets or env vars before the backend functions fully:
- `SUPABASE_URL` — Your Supabase project URL
- `SUPABASE_ANON_KEY` — Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase service role key (server-side only)
- `SUPABASE_JWT_SECRET` — For JWT validation
- `APP_SECRET_KEY` — App-level secret key
- `MPESA_CONSUMER_KEY` — M-Pesa API consumer key
- `MPESA_CONSUMER_SECRET` — M-Pesa API consumer secret
- `MPESA_PASSKEY` — M-Pesa passkey
- `AT_API_KEY` — Africa's Talking API key

## Key Pages
- `/` → Landing page (index.html)
- `/pages/find-workers.html` — Browse fundis
- `/pages/post-job.html` — Post a job
- `/pages/client-dashboard.html` — Client dashboard
- `/pages/worker-dashboard.html` — Fundi dashboard
- `/pages/admin-dashboard.html` — Admin panel
- `/pages/login.html` — Authentication
- `/pages/register.html` — Registration

## Deployment
- Target: `autoscale`
- Run command: `node serve.js`
- Frontend serves on port 5000
