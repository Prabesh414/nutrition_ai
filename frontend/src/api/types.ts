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

export interface ApiHistoryPoint {
  date: string;
  calories_consumed: number;
  calories_target: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
  meal_count: number;
}

export interface ApiHistoryResponse {
  days: ApiHistoryPoint[];
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

export interface ApiWaterLog {
  id: number;
  amount_ml: number;
  log_date: string;
  logged_at: string | null;
}

export interface ApiWaterSummary {
  log_date: string;
  total_ml: number;
  target_ml: number;
  progress_pct: number;
  logs: ApiWaterLog[];
}

export interface WaterInput {
  amount_ml: number;
  log_date?: string;
}

export interface ApiAnalyticsSummary {
  period_days: number;
  streak_days: number;
  avg_calories: number;
  avg_protein_g: number;
  avg_carbs_g: number;
  avg_fat_g: number;
  avg_fiber_g: number;
  adherence_score_pct: number;
  days_logged: number;
  total_meals_logged: number;
  total_water_ml: number;
}

export interface ApiQuickLogItem {
  name: string;
  quantity: number;
  meal_type: MealType;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
  confidence: number;
}

export interface ApiQuickLogResponse {
  parsed_items: ApiQuickLogItem[];
  summary_note?: string;
  source: 'llm' | 'heuristic';
}

export interface ApiSubstitutionItem {
  food: ApiFood;
  original_food_name: string;
  serving_multiplier: number;
  adjusted_serving_size: string;
  adjusted_calories: number;
  adjusted_protein: number;
  adjusted_carbs: number;
  adjusted_fat: number;
  adjusted_fiber: number;
  match_score: number;
  reason: string;
}

export interface ApiSubstitutionResponse {
  original_food_id: number;
  original_food_name: string;
  substitutions: ApiSubstitutionItem[];
}

export interface ApiMealPlanSlotItem {
  food: ApiFood;
  servings: number;
  adjusted_serving: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
}

export interface ApiMealPlanSlot {
  meal_type: MealType;
  target_calories: number;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  total_fiber: number;
  items: ApiMealPlanSlotItem[];
}

export interface ApiMealPlanResponse {
  target_calories: number;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  total_fiber: number;
  adherence_pct: number;
  slots: ApiMealPlanSlot[];
  ai_tips?: string;
}

