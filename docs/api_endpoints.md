# API Endpoints Specification

This document details the REST API specifications provided by the **FastAPI Backend**.

## Base URL
`http://localhost:8000/api/v1`

---

## Authentication Endpoints

### 1. User Registration
* **Endpoint:** `POST /auth/register`
* **Description:** Register a new user.
* **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123"
  }
  ```
* **Success Response (201 Created):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "message": "User registered successfully"
  }
  ```

### 2. User Login
* **Endpoint:** `POST /auth/login`
* **Description:** Authenticate user and return JWT access token.
* **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123"
  }
  ```
* **Success Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

---

## Health Profile Endpoints

### 1. Get Profile
* **Endpoint:** `GET /profile`
* **Headers:** `Authorization: Bearer <token>`
* **Success Response (200 OK):**
  ```json
  {
    "age": 25,
    "gender": "Male",
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "activity_level": "Moderately Active",
    "fitness_goal": "Maintain Weight",
    "dietary_preference": "None",
    "bmi": 22.86,
    "bmr": 1680.5
  }
  ```

### 2. Create/Update Profile
* **Endpoint:** `PUT /profile`
* **Headers:** `Authorization: Bearer <token>`
* **Request Body:**
  ```json
  {
    "age": 25,
    "gender": "Male",
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "activity_level": "Moderately Active",
    "fitness_goal": "Maintain Weight",
    "dietary_preference": "None"
  }
  ```
* **Success Response (200 OK):**
  ```json
  {
    "message": "Profile updated successfully",
    "bmi": 22.86,
    "bmr": 1680.5
  }
  ```

---

## Food & Recommendation Endpoints

### 1. Search Foods
* **Endpoint:** `GET /foods`
* **Query Params:** `query` (string, search term), `category` (string, optional)
* **Success Response (200 OK):**
  ```json
  [
    {
      "id": 105,
      "name": "Oatmeal",
      "category": "Breakfast",
      "calories": 150.0,
      "protein_g": 5.0,
      "carbs_g": 27.0,
      "fat_g": 3.0,
      "fiber_g": 4.0,
      "serving_size": "1 cup"
    }
  ]
  ```

### 2. Get Personalized Recommendations
* **Endpoint:** `GET /recommendations`
* **Headers:** `Authorization: Bearer <token>`
* **Success Response (200 OK):**
  ```json
  {
    "daily_targets": {
      "calories": 2100.0,
      "protein_g": 131.0,
      "carbs_g": 236.0,
      "fat_g": 70.0
    },
    "recommendations": [
      {
        "meal_type": "Breakfast",
        "options": [
          { "id": 105, "name": "Oatmeal", "calories": 150.0 },
          { "id": 112, "name": "Greek Yogurt", "calories": 120.0 }
        ]
      }
    ]
  }
  ```

---

## Tracking & Dashboard Endpoints

### 1. Log Consumed Meal
* **Endpoint:** `POST /logs`
* **Headers:** `Authorization: Bearer <token>`
* **Request Body:**
  ```json
  {
    "food_item_id": 105,
    "quantity": 1.5,
    "meal_type": "Breakfast",
    "date": "2026-08-10"
  }
  ```
* **Success Response (201 Created):**
  ```json
  {
    "message": "Meal logged successfully",
    "daily_totals": {
      "calories": 225.0,
      "protein_g": 7.5,
      "carbs_g": 40.5,
      "fat_g": 4.5
    }
  }
  ```

### 2. Get Daily Progress
* **Endpoint:** `GET /logs/progress`
* **Headers:** `Authorization: Bearer <token>`
* **Query Params:** `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD)
* **Success Response (200 OK):**
  ```json
  [
    {
      "date": "2026-08-10",
      "calories_consumed": 1850.0,
      "target_calories": 2100.0
    }
  ]
  ```

---

## Chatbot Endpoints

### 1. Send Message
* **Endpoint:** `POST /chatbot`
* **Headers:** `Authorization: Bearer <token>`
* **Request Body:**
  ```json
  {
    "message": "Should I eat oatmeal or eggs for breakfast for weight loss?"
  }
  ```
* **Success Response (200 OK):**
  ```json
  {
    "response": "Both are excellent choices. Oatmeal provides complex carbohydrates and fiber, keeping you full longer. Eggs offer high-quality protein, which supports muscle maintenance and satiety. A combination of both or rotating them is ideal."
  }
  ```
