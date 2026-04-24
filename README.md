# KaziX — Hire Trusted Fundis in Kenya

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com/)

KaziX is a modern marketplace designed to bridge the trust gap between skilled Kenyan workers (fundis) and clients. By integrating M-Pesa escrow payments, ID verification, and a transparent review system, KaziX provides a secure and efficient ecosystem for the local service industry.

## 🌟 Key Features

### For Clients
- **Verified Professionals:** Browse through a curated list of plumbers, electricians, painters, and more, all with verified IDs.
- **Secure Escrow Payments:** Funds are held securely and only released when you confirm the job is done to your satisfaction.
- **Rapid Response:** Average hiring time of under 8 minutes.
- **Transparency:** Real client reviews and ratings to guide your choices.

### For Pros (Fundis)
- **Instant SMS Alerts:** Receive real-time notifications for job opportunities in your area.
- **Guaranteed Payment:** Work with peace of mind knowing the client's payment is secured in escrow before you start.
- **Business Growth:** Build a digital reputation with a verified profile and positive feedback.
- **Seamless M-Pesa Integration:** Get paid directly to your phone within minutes of job completion.

## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
- **Frontend:** Modern Vanilla HTML5, CSS3, and JavaScript.
- **Database & Auth:** [Supabase](https://supabase.com/)
- **Payments:** [Safaricom Daraja API](https://developer.safaricom.co.ke/) (M-Pesa)
- **Notifications:** [Africa's Talking SMS API](https://africastalking.com/)
- **Design:** Modern Brutalist aesthetic, mobile-first approach.
  - **Typography:** `Syne` for branding, `DM Sans` for content.

## 📁 Project Structure

```text
KaziX/
├── backend/                # FastAPI Application
│   ├── app/                # Core logic, routes, and models
│   ├── tests/              # Backend test suite
│   └── supabase/           # Migrations and seed data
├── frontend/               # Static Frontend Assets
│   ├── pages/              # HTML templates
│   └── assets/             # CSS and JS files
├── Agents.md               # AI Instructions & Versioning
├── Planning.md             # Project Milestones
└── Tasks.md                # Pending Tasks
```

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Supabase account and project
- M-Pesa Daraja API credentials (Sandbox or Production)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/kazix.git
   cd kazix
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment Variables:**
   Create a `.env` file in the `backend/` directory (refer to `backend/app/core/config.py` for required variables).

4. **Run the Application:**
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   The site will be available at `http://localhost:8000`.

## 🧪 Testing

Run the backend test suite:
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:.
python3 -m pytest
```
### ⚙️ Frontend Environment Setup

The frontend requires an `env.js` file to connect to Supabase. This is generated from a `.env` file in the `frontend/` directory.

1. Create `frontend/.env` with your Supabase credentials:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   ```
2. Generate the `env.js` file:
   ```bash
   node frontend/generate-env.js
   ```

Open `http://localhost:8000/` for the website and `http://localhost:8000/docs` for API docs in development.

## 🇰🇪 Built for Kenya
KaziX is specifically engineered for the Kenyan context, focusing on mobile-first accessibility and deep integration with M-Pesa workflows to ensure financial security and trust.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
