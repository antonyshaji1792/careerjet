# CareerJet — AI-Powered Job Search Autopilot

> **Stop searching. Start interviewing.**
> CareerJet uses AI to discover, match, and automatically apply to the best jobs for you — across LinkedIn, Naukri, and more.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Celery](https://img.shields.io/badge/Celery-5.x-brightgreen.svg)](https://docs.celeryq.dev)

---

## Table of Contents

- [Overview](#overview)
- [Screenshots](#screenshots)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Running Background Workers](#running-background-workers)
- [First-Time Setup Walkthrough](#first-time-setup-walkthrough)
- [Project Structure](#project-structure)
- [System Architecture](#system-architecture)
- [Database Schema](#database-schema)
- [Admin Panel](#admin-panel)
- [Running Tests](#running-tests)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

CareerJet is a full-stack Flask web application that automates the entire job search lifecycle. It scrapes job listings from multiple platforms, scores them against your resume using AI, generates tailored cover letters, runs mock video interviews, and even submits applications for you — all while you sleep.

---

## Screenshots

### Landing Page
![CareerJet Landing Page](screenshots/landing.png)

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Resume Builder
![Resume Builder](screenshots/resume_builder.png)

### AI Video Interview
![Video Interview](screenshots/video_interview.png)

### Salary Coach
![Salary Coach](screenshots/salary_coach.png)

### Subscription Plans
![Pricing Plans](screenshots/pricing.png)

> **Note for contributors:** Place screenshots in a `screenshots/` folder at the project root. Recommended size: 1280×720px PNG.

---

## Features

### AI Autopilot
Automatically discovers jobs and submits applications on **LinkedIn** and **Naukri** based on your profile and preferences. Configure a daily application limit, preferred hours, and a match-score threshold — then let it run in the background.

### Smart Job Matching
Every scraped job is scored against your resume by the AI matching engine. Jobs above your threshold are queued for auto-apply; all scores are visible on the dashboard so you always know why a job was selected.

### ATS-Optimised Resume Builder
Build a resume from scratch or upload a PDF/DOCX. Features include:
- Real-time ATS scoring
- AI bullet-point rewriting
- Skill gap detection
- Multiple export templates (PDF, DOCX)
- Version history
- Recruiter persona simulation

### AI Cover Letter Generator
Generate tailored cover letters for any job posting in seconds. Save and reuse templates, edit inline, and export to PDF or DOCX.

### AI Video Interview Prep
Practice mock interviews with an AI recruiter that asks role-specific questions and evaluates your answers in real time. Review session reports and track improvement across sessions.

### Salary Coach
AI-powered salary negotiation coaching. Get data-driven advice on target compensation, how to respond to offers, and ready-to-use counter-offer templates.

### Job Alerts
Create keyword-based alerts for any platform. CareerJet monitors them continuously and surfaces new matches in your dashboard.

### Skill Gap Analysis
See exactly which skills your profile is missing for your target roles. Get ranked, personalised course recommendations to close each gap.

### Application Tracker
A unified view of every application — platform, date, status, response, and next steps — in one place.

### Multi-LLM Support
Switch between **OpenAI**, **Anthropic Claude**, **Google Gemini**, **Groq**, **Mistral**, **OpenRouter**, and local **Ollama** models from the admin settings panel — no code changes required.

### Credit-Based Subscription System
Transparent credit system with **Stripe** and **Razorpay** payment support. Credits are consumed only on successful AI operations. Pro plans include rollover protection.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask 3.x |
| Database | SQLite (dev) / PostgreSQL (prod), SQLAlchemy 2.x |
| Migrations | Flask-Migrate (Alembic) |
| Auth | Flask-Login, Flask-Bcrypt, Flask-JWT-Extended |
| Task Queue | Celery 5.x + Redis |
| Browser Automation | Selenium 4.x, Playwright |
| AI / NLP | OpenAI, Anthropic, Google Gemini, spaCy |
| PDF / Docs | ReportLab, xhtml2pdf, python-docx |
| Payments | Stripe, Razorpay |
| Frontend | Bootstrap 5, Vanilla JS, Font Awesome 6 |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.11+** | [python.org](https://www.python.org/downloads/) |
| **Redis** | Required for Celery. macOS: `brew install redis` · Ubuntu: `sudo apt install redis-server` · Windows: use WSL2 or [Redis for Windows](https://github.com/microsoftarchive/redis/releases) |
| **Google Chrome + ChromeDriver** | Required for LinkedIn / Naukri automation. [ChromeDriver](https://chromedriver.chromium.org/downloads) must match your Chrome version. |
| **Git** | For cloning the repo |

---

## Installation

### 1. Clone the repository

```bash
git clone [https://github.com/your-username/careerjet.git](https://github.com/antonyshaji1792/careerjet.git)
cd careerjet
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
playwright install chromium
```

### 5. Download the spaCy language model

```bash
python -m spacy download en_core_web_sm
```

---

## Configuration

### 1. Create your `.env` file

Create a file named `.env` in the project root with the following contents:

```env
# ─── Flask ────────────────────────────────────────────────────────────────────
SECRET_KEY=your-very-secret-key-change-this

# ─── Database ─────────────────────────────────────────────────────────────────
# SQLite (development)
DATABASE_URL=sqlite:///careerjet.db
# PostgreSQL (production)
# DATABASE_URL=postgresql://user:password@localhost:5432/careerjet

# ─── Redis ────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ─── Credential Encryption ────────────────────────────────────────────────────
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
LINKEDIN_ENCRYPTION_KEY=your-fernet-key-here

# ─── AI Providers (configure at least one) ────────────────────────────────────
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GEMINI_API_KEY=...
# GROQ_API_KEY=...
# MISTRAL_API_KEY=...
# OPENROUTER_API_KEY=...

# ─── Payments (optional) ──────────────────────────────────────────────────────
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=your_secret_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
```

### 2. Generate a Fernet encryption key

CareerJet encrypts all stored job portal credentials using Fernet (AES-128-CBC). Generate your key once and paste it into `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Initialise the database

```bash
flask db upgrade
```

If no `migrations/` folder exists yet:

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```

### 4. (Optional) Seed default prompts and subscription plans

```bash
python seed_prompts.py
```

---

## Running the Application

```bash
python run.py
```

The app starts at **http://localhost:5000**.

To use a custom port:

```bash
python run.py 8080
```

---

## Running Background Workers

The Autopilot and all async AI tasks run through Celery. Start these in separate terminal windows alongside the main app.

### Start Redis

```bash
redis-server
```

### Start the Celery worker

```bash
celery -A celery_worker.celery worker --loglevel=info
```

### Start Celery Beat (scheduled autopilot runs)

```bash
celery -A celery_worker.celery beat --loglevel=info
```

---

## First-Time Setup Walkthrough

1. **Register** an account at `/auth/register`.
2. **Upload your resume** at `/profile` — the AI will auto-fill your entire profile from the PDF or DOCX.
3. **Add job portal credentials** (LinkedIn / Naukri) at `/profile/settings`.
4. **Select your target platforms** at `/profile/websites` — choose which job boards to search.
5. **Create job alerts** at `/alerts` — add keywords, location, and minimum salary filters.
6. **Configure your Autopilot schedule** at `/profile/schedule`:
   - Set a daily application limit
   - Choose preferred days and hours
   - Set a minimum match-score threshold
7. **Enable Autopilot** and let CareerJet handle the rest.

---

## Project Structure

```
careerjet/
├── app/
│   ├── ai/                          # Prompt hardening, resume integrity guard
│   ├── blueprints/
│   │   └── resume/                  # Resume builder blueprint (routes + forms)
│   ├── models/                      # SQLAlchemy models (20+ files)
│   │   ├── user.py
│   │   ├── jobs.py
│   │   ├── resume.py
│   │   ├── profile.py
│   │   ├── skill_intelligence.py
│   │   └── ...
│   ├── resumes/                     # Resume parser, generator, template config
│   ├── routes/                      # Flask route blueprints
│   │   ├── auth.py
│   │   ├── jobs.py
│   │   ├── profile.py
│   │   ├── resume_api.py
│   │   ├── skill_gap_ui_api.py
│   │   └── ...
│   ├── services/                    # Core business logic
│   │   ├── autopilot.py             # Job discovery + auto-apply orchestrator
│   │   ├── linkedin_scraper.py      # LinkedIn job scraping
│   │   ├── naukri_scraper.py        # Naukri job scraping
│   │   ├── matching.py              # AI job-resume matching engine
│   │   ├── resume_service.py        # Resume processing
│   │   ├── resume_generation_service.py
│   │   ├── ats_scoring_service.py   # ATS score calculation
│   │   ├── skill_gap_service.py     # Skill gap analysis
│   │   ├── interview_prep.py        # Mock interview logic
│   │   ├── salary_coach.py          # Salary negotiation AI
│   │   ├── cover_letter_*.py        # Cover letter generation
│   │   └── ...
│   ├── tasks/
│   │   └── celery_tasks.py          # Celery task definitions
│   ├── templates/                   # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── dashboard/
│   │   ├── resume/
│   │   ├── interview/
│   │   ├── video_interview/
│   │   ├── cover_letters/
│   │   ├── salary/
│   │   ├── subscription/
│   │   └── admin/
│   └── utils/
│       └── human_behavior.py        # Human-mimicry for browser automation
├── migrations/                      # Alembic migration scripts
├── tests/                           # Pytest test suite
├── instance/                        # SQLite database (gitignored)
├── uploads/                         # User-uploaded resumes (gitignored)
├── .env                             # Environment variables (gitignored)
├── requirements.txt
├── run.py                           # App entry point
└── celery_worker.py                 # Celery worker entry point
```

---

## System Architecture

```
                        ┌─────────────────────┐
                        │   User's Browser     │
                        └────────┬────────────┘
                                 │ HTTP
                        ┌────────▼────────────┐
                        │   Flask App (run.py) │
                        │   Blueprints/Routes  │
                        └────────┬────────────┘
               ┌─────────────────┼─────────────────┐
               │                 │                  │
    ┌──────────▼──────┐  ┌───────▼───────┐  ┌──────▼──────────┐
    │  SQLAlchemy ORM │  │ AI Services   │  │ Celery Workers  │
    │  SQLite / PG    │  │ (OpenAI etc.) │  │ (Redis Broker)  │
    └─────────────────┘  └───────────────┘  └──────┬──────────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │  Browser Automation  │
                                         │  Selenium/Playwright │
                                         │  LinkedIn / Naukri   │
                                         └─────────────────────┘
```

### Data Flow

1. **Scheduled Triggers** — Celery Beat initiates scraping cycles on the configured interval.
2. **Headless Discovery** — Selenium/Playwright workers log in to job portals and scrape listings.
3. **De-duplication** — Scraped jobs are hashed and checked against the `JobPost` table before ingestion.
4. **AI Matching** — Each new job is scored against the user's resume using the configured LLM.
5. **Auto-Apply** — Jobs above the match threshold are submitted using platform-specific apply engines.
6. **Telemetry** — Every action is logged to the `Application` table and surfaced in the Dashboard.

### Credit Guard

All AI operations are wrapped in an atomic credit transaction:
- Credits are **reserved** before the API call.
- Credits are **finalised** only on success.
- On failure, the reservation is released — no credits are lost to network errors.

---

## Database Schema

### Identity & Profile
| Model | Purpose |
|---|---|
| `User` | Authentication, roles (Admin / Super Admin) |
| `UserProfile` | Skills, preferences, experience summary |
| `PersonalDetails` | Name, phone, address |
| `Employment` | Work history |
| `Education` | Academic history |

### Billing & Credits
| Model | Purpose |
|---|---|
| `Plan` | Subscription tiers (price, credit allocation, rollover rules) |
| `Subscription` | User ↔ Plan link with state (Active / Suspended) |
| `CreditWallet` | Available AI credits with atomic update locking |
| `CreditTransaction` | Full audit trail of every credit event |

### Job Search & Automation
| Model | Purpose |
|---|---|
| `JobPost` | Aggregated job data from all platforms |
| `JobMatch` | AI-calculated affinity scores per user per job |
| `Application` | Lifecycle tracking (Pending / Applied / Interviewing / Rejected) |
| `LinkedInJob` / `NaukriJob` | Platform-specific metadata |

### Career Tools
| Model | Purpose |
|---|---|
| `Resume` / `ResumeVersion` | Version-controlled resume files and AI optimisations |
| `CoverLetter` | Generated cover letters |
| `AIInterview` / `AIVideoInterview` | Mock interview sessions and AI feedback |

---

## Admin Panel

Promote a user to Super Admin:

```bash
python update_super_admin_password.py
```

Or via the Python shell:

```bash
python -c "
from app import create_app, db
from app.models import User
app = create_app()
with app.app_context():
    u = User.query.filter_by(email='your@email.com').first()
    u.is_admin = True
    u.is_super_admin = True
    db.session.commit()
    print('Done')
"
```

Admin features:
- **Dashboard** — platform-wide stats and health
- **LLM Config** — switch AI providers and API keys without redeployment
- **Subscription Plans** — create and edit credit plans
- **Autopilot Monitor** — view live autopilot runs per user
- **Support Tickets** — respond to contact form submissions
- **Audit Logs** — full decision and action log

**User Roles:**
- **Regular User** — full access to all job search and career tools
- **Admin** — access to admin dashboard and stats
- **Super Admin** — full system access, user management, global AI settings

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please ensure all new features include tests and that `pytest tests/` passes before submitting.

---

## License

This project is released under the [MIT License](LICENSE).

---

> Built with Flask, spaCy, Selenium, Playwright, and a lot of ☕
