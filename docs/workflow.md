# System Workflow

## Overview

The system workflow describes how a user interacts with the AI-Based Personalized Diet Recommendation and Nutrition Management System. It transitions from a linear onboarding phase to a cyclical daily tracking and engagement phase centered around the **User Dashboard**.

---

## Onboarding Workflow (Linear Phase)

When a user first joins the platform, they undergo a sequential onboarding process to set up their profile.

```text
                    START
                      |
                      v
               Register / Login
                      |
                      v
            Create Health Profile
            (Age, Height, Weight, etc.)
                      |
                      v
         System Calculates BMI / BMR
                      |
                      v
               Set Fitness Goal
            (Lose, Maintain, Gain)
                      |
                      v
         Initial Diet Recommendation
                      |
                      v
         Enter Dashboard (Central Hub)
```

---

## Daily Lifecycle Workflow (Cyclical Phase)

Once onboarding is complete, the user enters an iterative daily cycle where they manage, log, and interact with the application through the dashboard.

```text
                         +-----------------------------+
                         |       USER DASHBOARD        |
                         |        (Central Hub)        |
                         +--+--------+-------------+---+
                            |        |             |
            +---------------+        |             +---------------+
            |                        |                             |
            v                        v                             v
    +---------------+        +---------------+             +---------------+
    |  Log / Track  |        | Ask Nutrition |             |  Update Body  |
    |  Daily Meals  |        |    Chatbot    |             |    Metrics    |
    +-------+-------+        +-------+-------+             +-------+-------+
            |                        |                             |
            v                        v                             v
   [Query Food DB /         [AI generates advice          [System updates  ]
    Select Meal Option]      based on profile]             [BMI/BMR & plans]
            |                        |                             |
            +---------------+--------+-------------+---------------+
                            |
                            v
                Progress & Metrics Updated
                            |
                            v
               Return to Dashboard (Loop)
```

---

## Workflow Details

### 1. Registration & Onboarding
- **User Action:** Signs up with email/password and enters health metrics.
- **System Action:** Validates input, calculates baseline **BMI** and **BMR** (Mifflin-St Jeor), and persists metadata to the database.

### 2. Personalized Diet Engine Run
- **Trigger:** Profile creation or goal update.
- **System Action:** Executes the ML recommendation engine (Nearest Neighbors) using the user's target calorie/macronutrient requirements against the food dataset.

### 3. Dashboard Central Hub
- Serves as the user homepage displaying:
  - Daily calorie/macro target vs. current consumption progress bars.
  - Quick action buttons to log meals, chat, or update profile.
  - Weight loss/gain historical charts.

### 4. Interactive Cycle
- **Meal Logging:** Users search or select recommended foods, adjust serving sizes, and log them. Daily totals are updated.
- **AI Chat:** Users ask context-aware questions. The chatbot leverages the user profile and food logs to provide specific nutrition advice.
- **Target Recalculation:** As the user logs progress and updates their weight, the system dynamically shifts calorie targets.
