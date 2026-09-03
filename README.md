# AI-Based Personalized Diet Recommendation and Nutrition Management System

## Overview

This project is a final year BSc IT project that aims to develop an AI-based personalized diet recommendation and nutrition management system.

The system will analyse user health information together with nutritional food data to provide personalized food recommendations based on individual requirements, dietary preferences, and fitness goals.

The system will provide BMI and BMR calculations, food information, meal tracking, nutritional progress monitoring, personalized recommendations, and an AI-based nutrition chatbot.

The project will use publicly available nutritional data, primarily obtained from a suitable Kaggle dataset, as the basis for food analysis and recommendation development.

> **Note:** This system is intended as a general nutrition support and educational tool. It is not intended to replace professional medical or dietary advice.

---

## Problem Statement

Individuals may find it difficult to identify suitable food choices from large amounts of nutritional information, particularly when their nutritional requirements and fitness goals differ from those of other users.

Existing nutrition applications commonly provide food databases, calorie information, and tracking features, but users may still need to manually interpret nutritional information and determine which foods are appropriate for their individual requirements.

This project addresses this problem by developing a system that combines user health information with nutritional food data to provide personalized and data-driven food recommendations.

---

## Objectives

- Develop a secure user authentication system.
- Allow users to create and manage health profiles.
- Calculate BMI and BMR based on user information.
- Integrate a publicly available food and nutrition dataset.
- Analyse and preprocess nutritional data for recommendation development.
- Develop a machine-learning-based food recommendation component.
- Provide personalized food recommendations based on user requirements and goals.
- Allow users to search for nutritional information.
- Provide meal tracking functionality.
- Provide a dashboard for monitoring nutritional intake and progress.
- Develop an AI-based nutrition chatbot for general nutrition-related assistance.

---

## Main Features

### User Authentication
Users can register, log in, and securely manage their accounts.

### Social-Style Profile Access
Users can access a profile view from the top-right avatar area, similar to social platforms such as Instagram or Facebook. This provides quick access to personal health details and usage information without leaving the dashboard flow.

### Health Profile
Users can provide age, gender, height, weight, activity level, fitness goal, and dietary preference.

### BMI and BMR Calculation
Calculated dynamically using standard formulae (e.g., Mifflin-St Jeor) based on user metrics.

### Food Database
Nutritional dataset featuring calorie, protein, carbohydrate, fat, and fiber content per serving size.

### Personalized Recommendations
Leverages a machine learning model to recommend meals based on user targets.

### Meal Tracking & Progress Dashboard
Record daily meals and view progress charts reflecting nutrition goals vs. intake.

### Live Clock / Time Context
A live time display is included in the top navigation so users can track the current time while reviewing daily nutrition goals and activity.

### AI Nutrition Chatbot
Provides conversational nutritional assistance, drawing context from food logs and profiles.

### Usage & Token Tracker
The app includes a lightweight usage monitor to estimate AI consumption for coaching prompts and daily activity within the session.

---

## System Overview

```text
                         User
                           |
                           v
                    React Frontend
                           |
                           v
                    FastAPI Backend
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
        PostgreSQL    ML Engine      Chatbot
             |             |             |
             |             v             |
             |      Recommendations      |
             |                           |
             +-------------+-------------+
                           |
                           v
                    User Dashboard
```

---

## Project Documentation

Detailed system documents have been created under the [docs/](file:///c:/Users/prabe/Desktop/nutrition_ai/docs/) directory:

1. **[System Workflow](file:///c:/Users/prabe/Desktop/nutrition_ai/docs/workflow.md)** – Detailed user onboarding flow and cyclical daily lifecycle.
2. **[System Architecture](file:///c:/Users/prabe/Desktop/nutrition_ai/docs/architecture.md)** – Client-server stack layout, component roles, and API flow.
3. **[Database Schema](file:///c:/Users/prabe/Desktop/nutrition_ai/docs/database_schema.md)** – PostgreSQL entity-relationship design and table specifications.
4. **[API Endpoints](file:///c:/Users/prabe/Desktop/nutrition_ai/docs/api_endpoints.md)** – RESTful routing specifications for auth, profile, recommendations, tracking, and chatbot.
5. **[Recommendation & ML Engine](file:///c:/Users/prabe/Desktop/nutrition_ai/docs/ml_model.md)** – Mathematical modeling (Mifflin-St Jeor, KNN Cosine Similarity) and recommendation pipeline logic.

---

## Changelog
To see the history of changes made to the documentation and design, check the **[CHANGELOG.md](file:///c:/Users/prabe/Desktop/nutrition_ai/CHANGELOG.md)**.

