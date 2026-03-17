# CrowdTest (working name)

Social simulation engine for testing marketing materials against AI-generated crowds.

## What it does

Submit marketing material → system generates a crowd of AI personas → runs a social simulation → produces engagement scores, a simulated social feed, and actionable recommendations.

## Architecture

```
frontend/          Next.js + React + Tailwind
backend/           Python + FastAPI
  app/
    api/v1/        REST endpoints
    core/          Config, auth, database
    models/        SQLAlchemy models
    schemas/       Pydantic schemas
    services/
      simulation/  The engine (personas, social graph, runner, scoring)
    workers/       Celery async tasks
```

## Quick Start

```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Cost Model

Optimized for profitability: batched Haiku calls + engagement filtering = $0.05-$0.15 per simulation. See `../plan.md` §12 for details.
