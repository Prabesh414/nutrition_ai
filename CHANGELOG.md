# Changelog

This document tracks changes, documentation additions, and configuration updates made to the **AI-Based Personalized Diet Recommendation and Nutrition Management System** repository.

---

## [Profile Access, Clock, and Usage Tracking Update] - 2026-09-02

### Added
- **Social-style profile access**: A profile/avatar button was added to the top-right corner of the app so users can open a dedicated profile view from the main navigation.
- **Live clock display**: A real-time clock was added to the top-right area of the app to support daily activity awareness and give the interface a more polished social-style feel.
- **Usage/token tracker**: A lightweight usage monitor was added to estimate AI coaching consumption based on prompts and meal-tracking activity within the session.
- **Profile detail view**: A dedicated profile page displays key health metrics, goals, and app usage in a cleaner layout.

### Changed
- **[README.md](README.md)**: Updated to include the new profile access workflow, live time functionality, and usage tracking overview.
- **Frontend navigation flow**: The dashboard navigation now supports a profile toggle while preserving the existing nutrition dashboard and AI coach experience.

---

## [Initial Setup & Documentation Update] - 2026-08-10

### Added
- **[.gitignore](.gitignore)**: Roots Git ignore rules for ignoring frontend Node modules, Python venv, and local databases/.env secrets (allows tracking `.env.example`).
- **[.env.example](.env.example)**: Moved to root. Setup with environment templates for both FastAPI backend and React/Vite frontend.
- **[requirements.txt](requirements.txt)**: Python backend dependency definitions (FastAPI, SQLAlchemy, Scikit-learn, Pandas, Ollama).
- **[frontend/](frontend/)**: Initialized React frontend application scaffolded using Vite and configured with **TypeScript** and Bun.
- **[backend/](backend/)**: Initialized FastAPI backend scaffold containing `main.py` router skeleton, `database.py` configurations (SQLAlchemy setup), and `.env` template (configured for local Ollama service).
- **[System Architecture](docs/architecture.md)**: Detailed core stack components (React + FastAPI + PostgreSQL + ML Engine + Ollama Chatbot).
- **[Database Schema](docs/database_schema.md)**: Designed PostgreSQL ERD and table specifications (`users`, `health_profiles`, `food_items`, `daily_logs`, `log_items`, `chat_logs`).
- **[API Endpoints](docs/api_endpoints.md)**: Created FastAPI routing schemas for authentication, profile metrics, tracking logs, and chatbot queries.
- **[ML Engine Design](docs/ml_model.md)**: Documented Mifflin-St Jeor math targets and KNN Cosine Similarity recommendation algorithm with code snippets.

### Changed
- **[README.md](README.md)**: Rewritten in UTF-8 formatting and updated with quick links to all newly created design docs.
- **[System Workflow](docs/workflow.md)**: Redesigned the workflow diagram to shift from a linear structure to an onboarding (linear) and daily lifecycle (cyclical) tracking system.
