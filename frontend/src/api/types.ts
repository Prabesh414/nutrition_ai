/** Response shapes returned by the FastAPI backend (snake_case, as sent). */

export type Gender = 'Male' | 'Female' | 'Other';
export type ActivityLevel = 'Sedentary' | 'Lightly Active' | 'Moderately Active' | 'Very Active';
export type FitnessGoal = 'Lose Weight' | 'Maintain Weight' | 'Gain Weight';
export type DietaryPreference = 'None' | 'Vegetarian' | 'Vegan';
export type MealType = 'Breakfast' | 'Lunch' | 'Dinner' | 'Snack';

export const ACTIVITY_LEVELS: readonly ActivityLevel[] = [
  'Sedentary', 'Lightly Active', 'Moderately Active', 'Very Active',
];
export const FITNESS_GOALS: readonly FitnessGoal[] = [
  'Lose Weight', 'Maintain Weight', 'Gain Weight',
];
export const DIETARY_PREFERENCES: readonly DietaryPreference[] = [
  'None', 'Vegetarian', 'Vegan',
];
export const MEAL_TYPES: readonly MealType[] = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];

export interface ApiProfile {
  age: number;
  gender: Gender;
  height: number;
  weight: number;
  activity_level: ActivityLevel;
  fitness_goal: FitnessGoal;
  dietary_preference: DietaryPreference;
  profile_image_url: string | null;
  bmi: number;
  bmr: number;
  target_calories: number;
  target_protein: number;
  target_carbs: number;
  target_fat: number;
}

export interface ApiUser {
  id: number;
  username: string | null;
  first_name: string | null;
  middle_name: string | null;
  last_name: string | null;
  email: string;
  profile: ApiProfile | null;
}

export interface ApiAuthResponse {
  access_token: string;
  token_type: 'bearer';
  user: ApiUser;
}

export interface ApiMeal {
  id: number;
  name: string;
  quantity: number;
  meal_type: MealType;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
  log_date: string;
}

export interface ApiNutrientTotals {
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
}

export interface ApiDailySummary {
  log_date: string;
  consumed: ApiNutrientTotals;
  targets: ApiNutrientTotals;
  remaining: ApiNutrientTotals;
  meals: ApiMeal[];
}

export interface ApiFood {
  id: number;
  name: string;
  serving_size: string;
  region: string;
  calories: number;
  fat: number;
  carbohydrates: number;
  protein: number;
  fiber: number;
  sugars: number;
  is_vegetarian: boolean;
  is_vegan: boolean;
}

export interface ApiRecommendation extends ApiFood {
  similarity_score: number;
}

export interface ApiDailyTargets {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
}

export interface ApiRecommendationsResponse {
  daily_targets: ApiDailyTargets;
  consumed_today: ApiDailyTargets;
  next_meal_targets: ApiDailyTargets;
  recommendations: ApiRecommendation[];
}

export interface ApiChatResponse {
  reply: string;
  source: 'llm' | 'rules';
}

export interface ProfileInput {
  age: number;
  gender: Gender;
  height: number;
  weight: number;
  activity_level: ActivityLevel;
  fitness_goal: FitnessGoal;
  dietary_preference: DietaryPreference;
  profile_image_url?: string | null;
}

export interface MealInput {
  name: string;
  quantity?: number;
  meal_type: MealType;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber?: number;
  log_date?: string;
}
