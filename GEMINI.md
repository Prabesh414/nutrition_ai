# Project Instructions - Nutrition AI

Welcome to the **AI-Based Personalized Diet Recommendation and Nutrition Management System** repository. This file serves as the definitive reference for the team-shared engineering standards, architecture, and development workflows. All agents and developers must strictly adhere to these guidelines.

---

## Technical Stack

### Backend (Python / FastAPI)
- **Framework:** FastAPI
- **Database ORM:** SQLAlchemy 2.0+ (using asynchronous-ready `SessionLocal` patterns)
- **Database Driver:** `psycopg2-binary` (PostgreSQL)
- **ML & Recommendation Engine:** `scikit-learn`, `pandas`, `numpy` (using Mifflin-St Jeor formula and Cosine Similarity / KNN)
- **LLM Integration:** Ollama Local LLM Integration (e.g. Llama 3)
- **Security:** `python-jose` for JWT tokens, `passlib[bcrypt]` for secure hashing.

### Frontend (React / TypeScript)
- **Framework:** React 19 + TypeScript 6.0
- **Build Tool:** Vite 8
- **Linter:** `oxlint` (extremely fast linter configured via `.oxlintrc.json`)
- **Styling:** Vanilla CSS & Tailwind CSS
- **Features:** Live clock, user token & usage tracker, profile popover access in navigation.

---

## Codebase Architecture & Structure

```text
C:\Users\prabe\Desktop\nutrition_ai\
├───backend\                   # FastAPI application
│   ├───database.py            # SQLAlchemy setup, models, and session management
│   └───main.py                # App entry point, API routers, and business logic
├───frontend\                  # React + TypeScript Vite frontend
│   ├───src\
│   │   ├───App.tsx            # Main application component
│   │   ├───main.tsx           # Entry point
│   │   ├───App.css / index.css
│   │   └───assets\            # Static assets (images, icons)
├───tests\                     # Pytest suite
│   ├───test_auth_endpoints.py
│   └───test_profile_image_persistence.py
└───docs\                      # Detailed design & flow specifications
```

---

## Development Workflows

### 1. Research -> Strategy -> Execution Lifecycle
- **Research:** Map the codebase before writing code. Identify existing conventions, schemas, and design patterns.
- **Strategy:** Outline your design/architecture. Ensure it aligns with existing layers.
- **Execution:** Follow the **Plan -> Act -> Validate** cycle for every single change.

### 2. Implementation Guidelines
- **Zero Warnings/Hack-free Code:** Never use typescript casts (`as any`), suppress compiler/linter warnings, or use reflection/prototype hacks. Write type-safe, explicit code.
- **Composition over Inheritance:** Prioritize composition, wrapper classes, or standard React hooks/components over complex class inheritance.
- **Strict Linting:** Always run `oxlint` in the frontend and fix any formatting/syntax errors before committing.
- **No Direct Commit/Stage:** Never automatically stage or commit files unless explicitly directed.

### 3. Testing Standards
- **Pytest Suite:** All backend tests are located in `tests/` and are written using Pytest-style standalone functions (`def test_*`).
- **Test Command:**
  To run tests, ensure `pytest` is installed in your python environment, then run:
  ```bash
  pytest
  ```
- **Mandatory Test Updates:** Every feature addition or bug fix MUST be accompanied by a corresponding unit test in `tests/` to verify its correctness.

### 4. Running the App Locally
- **Backend Setup:**
  Run the backend using the provided batch or PowerShell scripts which automatically load the cloud Database URL:
  ```powershell
  # Windows PowerShell
  ./run_backend.ps1
  
  # Command Prompt
  run_backend.bat
  ```
- **Frontend Setup:**
  Navigate to the `frontend/` directory and run:
  ```bash
  npm run dev
  ```
