# AI-Powered Adaptive Study Planner

## Project

The AI-Powered Adaptive Study Planner is a Django-based full-stack application built to help students organize study plans, track learning progress, generate quizzes, and receive adaptive guidance. It keeps student data private and uses a clean AI service layer to help personalize the experience without exposing secrets or over-trusting AI output.

## Problem

Students often struggle with scattered notes, inconsistent study routines, poor exam preparation, and no insight into which topics deserve more attention. Many tools track tasks but do not adapt based on actual performance or provide personalized study guidance.

## Solution

This application combines a student profile, subjects and topics, AI-generated planning, progress tracking, quizzes, and recommendation logic into one workflow. The AI agent reads real application data, validates the response, and saves only safe, consistent tasks and quiz outcomes.

## Features

- Student registration, login, logout, and profile management
- Subject and topic management
- AI-generated study plans with validation
- Daily and weekly task tracking
- Progress updates for completion, score, time, and confidence
- Adaptive plan changes based on weak topics and low performance
- AI-generated quiz support
- Personalized recommendations and AI assistant responses
- Secure user-specific data access

## AI Agent

The AI architecture is split into a clean service and agent layer. The app uses `planner/ai` for dedicated planner structure and `planner/services.py` for backend validation and orchestration.

- `planner/ai/tools.py` exposes application-safe tools for student profile, subject list, progress, and recommendation data
- `planner/ai/planner_engine.py` coordinates the planning workflow
- `planner/ai/prompts.py` centralizes the AI prompts
- `planner/services.py` handles validation and database persistence

The planner uses real student data and validates AI-generated JSON before saving. It does not trust AI output blindly and rejects invalid or unsafe records.

## Tech Stack

- Python
- Django
- SQLite for local development
- HTML, CSS, JavaScript, Django templates
- AI API integration via environment-configured OpenAI-compatible APIs

## Architecture

1. Student registers and completes profile.
2. Student adds subjects and topics.
3. Django gathers real data and sends it to the AI planner.
4. AI generates structured tasks in JSON.
5. Backend validates the payload against subject/topic and date constraints.
6. Valid tasks are saved as study plans.
7. Student updates task status and progress.
8. Weak topics and low performance trigger plan adaptation.
9. AI recommendations and assistant answers use the same student data.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Environment Variables

Copy `.env.example` to `.env` and configure the values you need:

```text
SECRET_KEY=replace-with-a-strong-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
AI_API_KEY=
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
DATABASE_URL=sqlite:///db.sqlite3
```

## Database Setup

```bash
python manage.py makemigrations planner
python manage.py migrate
```

## Run

```bash
python manage.py runserver
```

Then open `http://localhost:8000/`.

## Testing

```bash
python manage.py test
```

## Deployment

For production, configure a secure secret key, enable debug off, set `ALLOWED_HOSTS`, and use production-ready database settings such as PostgreSQL or MySQL. Keep the AI API key in environment variables and never commit secrets.
