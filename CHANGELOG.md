# Changelog

This document tracks changes, documentation additions, and configuration updates made to the **AI-Based Personalized Diet Recommendation and Nutrition Management System** repository.

---

## [Initial Setup & Documentation Update] - 2026-08-10

### Added
- **[requirements.txt](requirements.txt)**: Python backend dependency definitions (FastAPI, SQLAlchemy, Scikit-learn, Pandas, Gemini API).
- **[System Architecture](docs/architecture.md)**: Detailed core stack components (React + FastAPI + PostgreSQL + ML Engine + Gemini Chatbot).
- **[Database Schema](docs/database_schema.md)**: Designed PostgreSQL ERD and table specifications (`users`, `health_profiles`, `food_items`, `daily_logs`, `log_items`, `chat_logs`).
- **[API Endpoints](docs/api_endpoints.md)**: Created FastAPI routing schemas for authentication, profile metrics, tracking logs, and chatbot queries.
- **[ML Engine Design](docs/ml_model.md)**: Documented Mifflin-St Jeor math targets and KNN Cosine Similarity recommendation algorithm with code snippets.

### Changed
- **[README.md](README.md)**: Rewritten in UTF-8 formatting and updated with quick links to all newly created design docs.
- **[System Workflow](docs/workflow.md)**: Redesigned the workflow diagram to shift from a linear structure to an onboarding (linear) and daily lifecycle (cyclical) tracking system.
