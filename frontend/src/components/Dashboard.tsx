import { useEffect, useRef, useState } from 'react';

import { api } from '../api/client';
import type { ApiDailySummary, ApiFood, ApiProfile, ApiRecommendation, MealType } from '../api/types';
import { MEAL_TYPES } from '../api/types';

interface DashboardProps {
  profile: ApiProfile | null;
  summary: ApiDailySummary | null;
  recommendations: ApiRecommendation[];
  loadingRecommendations: boolean;
  error: string | null;
  onLogMeal: (food: ApiFood, quantity: number, mealType: MealType) => Promise<void>;
  onRemoveMeal: (mealId: number) => Promise<void>;
}

function percent(value: number, target: number): number {
  if (!target) return 0;
  return Math.min((value / target) * 100, 100);
}

function round(value: number): number {
  return Math.round(value);
}

/** Suggests the meal slot the user is most likely logging right now. */
function suggestedMealType(now: Date = new Date()): MealType {
  const hour = now.getHours();
  if (hour < 11) return 'Breakfast';
  if (hour < 16) return 'Lunch';
  if (hour < 21) return 'Dinner';
  return 'Snack';
}

function MacroBar({ label, consumed, target, className }: {
  label: string;
  consumed: number;
  target: number;
  className: string;
}) {
  return (
    <div className="macro-progress-box">
      <div className="macro-lbl">{label}</div>
      <div className="macro-bar-bg">
        <div
          className={`macro-bar-fill ${className}`}
          style={{ height: `${percent(consumed, target)}%` }}
        />
      </div>
      <span className="macro-text">{round(consumed)}g / {round(target)}g</span>
    </div>
  );
}

function LogMealCard({ onLogMeal }: Pick<DashboardProps, 'onLogMeal'>) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ApiFood[]>([]);
  const [selected, setSelected] = useState<ApiFood | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [mealType, setMealType] = useState<MealType>(() => suggestedMealType());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  // Debounced, abortable search so each keystroke does not race the last.
  useEffect(() => {
    if (!query.trim() || selected?.name === query) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .searchFoods(query, controller.signal)
        .then(setResults)
        .catch(() => setResults([]));
    }, 250);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, selected]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected || saving) return;

    setSaving(true);
    setMessage(null);
    try {
      await onLogMeal(selected, quantity, mealType);
      setSelected(null);
      setQuery('');
      setQuantity(1);
      setResults([]);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not log that meal.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dashboard-card log-meal-card">
      <h3>Track a Meal</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-field-container">
          <label htmlFor="food-search">Search Food</label>
          <input
            id="food-search"
            type="text"
            className="form-input"
            placeholder="Type to search (e.g. Eggs, Oatmeal...)"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSelected(null);
            }}
            autoComplete="off"
          />
          {results.length > 0 && (
            <div className="search-dropdown">
              {results.slice(0, 8).map((food) => (
                <button
                  key={food.id}
                  type="button"
                  className="dropdown-item"
                  onClick={() => {
                    setSelected(food);
                    setQuery(food.name);
                    setResults([]);
                  }}
                >
                  <span>{food.name}</span>
                  <span className="dropdown-item-meta">({round(food.calories)} kcal)</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {selected && (
          <div className="selected-food-details">
            Selected: <strong>{selected.name}</strong> — {round(selected.calories)} kcal per{' '}
            {selected.serving_size}
          </div>
        )}

        <div className="log-row">
          <div className="form-field-container">
            <label htmlFor="meal-qty">Servings / Quantity</label>
            <input
              id="meal-qty"
              type="number"
              min="0.25"
              step="0.25"
              className="form-input"
              value={quantity}
              onChange={(event) => setQuantity(parseFloat(event.target.value) || 1)}
            />
          </div>
          <div className="form-field-container">
            <label htmlFor="meal-type">Meal Type</label>
            <select
              id="meal-type"
              className="form-input"
              value={mealType}
              onChange={(event) => setMealType(event.target.value as MealType)}
            >
              {MEAL_TYPES.map((type) => <option key={type}>{type}</option>)}
            </select>
          </div>
        </div>

        {message && <p className="form-error">{message}</p>}

        <button
          type="submit"
          className="btn-flat-primary log-meal-submit"
          disabled={!selected || saving}
        >
          {saving ? 'Logging…' : 'Log Meal'}
        </button>
      </form>
    </div>
  );
}

function RecommendationsCard({
  profile,
  recommendations,
  loadingRecommendations,
  onLogMeal,
}: Pick<DashboardProps, 'profile' | 'recommendations' | 'loadingRecommendations' | 'onLogMeal'>) {
  const [logging, setLogging] = useState<number | null>(null);
  const defaultMealType = useRef<MealType>(suggestedMealType());

  return (
    <div className="dashboard-card recommendations-card">
      <div className="card-header-with-badge">
        <h3>Smart Diet Recommendations</h3>
        <span className="pref-badge">
          {profile?.dietary_preference ?? 'None'} • {profile?.fitness_goal ?? 'Maintain Weight'}
        </span>
      </div>
      <p className="recommendations-intro">
        Foods closest to the nutrients you still have left today. Click <strong>+ Log</strong> to
        add one as your {defaultMealType.current.toLowerCase()}.
      </p>

      <div className="recommended-meals-list">
        {loadingRecommendations && (
          <p className="empty-logs-text">Loading personalized recommendations…</p>
        )}

        {!loadingRecommendations && recommendations.length === 0 && (
          <p className="empty-logs-text">
            No recommendations available. Set up your health profile to get started.
          </p>
        )}

        {!loadingRecommendations && recommendations.map((food) => (
          <div key={food.id} className="recommended-meal-item">
            <div className="rec-item-header">
              <div className="rec-title-wrap">
                <span className="rec-meal-badge">{food.region}</span>
                <strong className="rec-name">{food.name}</strong>
                <span className="rec-portion">Portion: {food.serving_size}</span>
              </div>
              <button
                type="button"
                className="btn-log-recommendation"
                disabled={logging === food.id}
                onClick={async () => {
                  setLogging(food.id);
                  try {
                    await onLogMeal(food, 1, defaultMealType.current);
                  } finally {
                    setLogging(null);
                  }
                }}
                title={`Log ${food.name}`}
              >
                {logging === food.id ? '…' : '+ Log'}
              </button>
            </div>
            <p className="rec-benefits">
              {Math.round(food.similarity_score * 100)}% match to your remaining targets
              {food.protein > 15 ? ' · rich in protein' : food.fiber > 3 ? ' · high in fibre' : ''}
            </p>
            <div className="rec-macros-row">
              <span className="rec-macro-pill cal-pill">{round(food.calories)} kcal</span>
              <span className="rec-macro-pill prot-pill">P: {food.protein}g</span>
              <span className="rec-macro-pill carb-pill">C: {food.carbohydrates}g</span>
              <span className="rec-macro-pill fat-pill">F: {food.fat}g</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Dashboard({
  profile,
  summary,
  recommendations,
  loadingRecommendations,
  error,
  onLogMeal,
  onRemoveMeal,
}: DashboardProps) {
  const consumed = summary?.consumed ?? { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 };
  const targets = summary?.targets ?? { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 };
  const meals = summary?.meals ?? [];

  return (
    <div className="dashboard-grid">
      <div className="dashboard-left">
        <div className="dashboard-card profile-metrics-card">
          <h3>Your Health Profile</h3>
          <div className="profile-stats">
            <div className="stat-box">
              <span className="stat-lbl">BMI</span>
              <span className="stat-val">{profile?.bmi ?? '—'}</span>
            </div>
            <div className="stat-box">
              <span className="stat-lbl">BMR</span>
              <span className="stat-val">{profile?.bmr ?? '—'} kcal</span>
            </div>
            <div className="stat-box">
              <span className="stat-lbl">Daily Budget</span>
              <span className="stat-val">{profile?.target_calories ?? '—'} kcal</span>
            </div>
          </div>
          <div className="profile-details-list">
            <p><strong>Goal:</strong> {profile?.fitness_goal ?? 'Not set'}</p>
            <p><strong>Preference:</strong> {profile?.dietary_preference ?? 'Not set'}</p>
            <p><strong>Activity Level:</strong> {profile?.activity_level ?? 'Not set'}</p>
          </div>
        </div>

        <div className="dashboard-card progress-card">
          <h3>Today&apos;s Consumption Progress</h3>
          {error && <p className="form-error">{error}</p>}
          <div className="metric-progress-wrapper">
            <div className="metric-header">
              <span>Calories</span>
              <span>{round(consumed.calories)} / {round(targets.calories)} kcal</span>
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill cal-fill"
                style={{ width: `${percent(consumed.calories, targets.calories)}%` }}
              />
            </div>
          </div>

          <div className="macros-progress-grid">
            <MacroBar label="Protein" consumed={consumed.protein} target={targets.protein} className="prot-fill" />
            <MacroBar label="Carbs" consumed={consumed.carbs} target={targets.carbs} className="carb-fill" />
            <MacroBar label="Fat" consumed={consumed.fat} target={targets.fat} className="fat-fill" />
          </div>
        </div>

        <LogMealCard onLogMeal={onLogMeal} />
      </div>

      <div className="dashboard-right">
        <RecommendationsCard
          profile={profile}
          recommendations={recommendations}
          loadingRecommendations={loadingRecommendations}
          onLogMeal={onLogMeal}
        />

        <div className="dashboard-card meal-history-card">
          <h3>Today&apos;s Meal Log</h3>
          {meals.length > 0 ? (
            <div className="logged-meals-list">
              {meals.map((meal) => (
                <div key={meal.id} className="logged-meal-item">
                  <div className="meal-details">
                    <span className="meal-title-name">{meal.name}</span>
                    <span className="meal-meta">
                      {meal.meal_type} • {meal.quantity} serving(s)
                    </span>
                  </div>
                  <div className="meal-macros-summary">
                    <span>{round(meal.calories)} kcal</span>
                    <button
                      className="btn-remove-meal"
                      onClick={() => void onRemoveMeal(meal.id)}
                      aria-label={`Remove ${meal.name}`}
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-logs-text">
              No meals logged today yet. Use the form to start tracking.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
