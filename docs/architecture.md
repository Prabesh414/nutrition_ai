# System Architecture

This document describes the high-level architecture of the **AI-Based Personalized Diet Recommendation and Nutrition Management System**.

## Architectural Overview

The system follows a modern decoupled client-server architecture:

```text
                     +-----------------------------------+
                     |           React Frontend          |
                     |       (User Interface & UX)       |
                     +-----------------+-----------------+
                                       |
                                       | HTTPS / JSON
                                       v
                     +-----------------+-----------------+
                     |          FastAPI Backend          |
                     |        (Application Logic)        |
                     +---+-------------+-------------+---+
                         |             |             |
        SQLAlchemy (ORM) |             |             | REST API / SDK
                         v             |             v
              +----------+---------+   |   +---------+---------+
              | PostgreSQL Database|   |   |   Gemini/LLM API  |
              |   (User & Log Data)|   |   | (Nutrition Chatbot|
              +--------------------+   v   +-------------------+
                             +---------+---------+
                             |     Scikit-Learn  |
                             |  Recommendation   |
                             |      Engine       |
                             +-------------------+
```

---

## Component Details

### 1. Frontend (React)
- **Role:** Interactive UI/UX.
- **Key Libraries:** 
  - React Router (Navigation)
  - Axios (API requests)
  - Chart.js / Recharts (Progress visualization & Dashboard)
  - Tailwind CSS / Vanilla CSS (Styling)

### 2. Backend (FastAPI)
- **Role:** Core business logic, secure authentication, API routing, and orchestration.
- **Key Features:**
  - High performance via asynchronous event loop.
  - Automatic OpenAPI (Swagger) documentation generation.
  - JWT-based authentication for secure session management.

### 3. Database (PostgreSQL)
- **Role:** Relational storage for structured transactional and analytical data.
- **Key Tables:** Users, Health Profiles, Food Items, Daily Logs, Chat History.

### 4. Recommendation Engine (Python / Scikit-Learn)
- **Role:** Processes user profile metrics (BMR, goals, preferences) and applies content-based filtering or clustering to generate personalized diet plans.
- **Core Algorithms:** Cosine Similarity, K-Means Clustering for food categorization.

### 5. Chatbot Service (LLM Integration)
- **Role:** Provides interactive nutritional advice.
- **Approach:** Integrates an LLM (e.g., Google Gemini API or OpenAI) with system prompting tailored for healthy living advice.
