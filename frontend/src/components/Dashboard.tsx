import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type {
  ApiDailySummary,
  ApiFood,
  ApiHistoryPoint,
  ApiProfile,
  ApiRecommendation,
  MealType,
} from '../api/types';
import { MEAL_TYPES } from '../api/types';
import { DateNavigator } from './DateNavigator';
import { WeeklyTrendsChart } from './WeeklyTrendsChart';

interface DashboardProps {
  profile: ApiProfile | null;
  summary: ApiDailySummary | null;
  recommendations: ApiRecommendation[];
  loadingRecommendations: boolean;
  history: ApiHistoryPoint[];
  loadingHistory: boolean;
  selectedDate: string;
  isToday: boolean;
  error: string | null;
  onPrevDay: () => void;
  onNextDay: () => void;
  onToday: () => void;
  onSelectDate: (date: string) => void;
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

function MacroBar({
  label,
  consumed,
  target,
  className,
}: {
  label: string;
  consumed: number;
  target: number;
  className: string;
}) {
  const pct = percent(consumed, target);
  return (
    <div className="macro-progress-box">
      <div className="macro-lbl">{label}</div>
      <div className="macro-bar-bg">
        <div className={`macro-bar-fill ${className}`} style={{ height: `${pct}%` }} />
      </div>
      <span className="macro-text">
        {round(consumed)}g / {round(target)}g
      </span>
      <span className="macro-percent">{round(pct)}%</span>
    </div>
  );
}

function LogMealCard({
  onLogMeal,
  selectedDate,
  isToday,
}: {
  onLogMeal: DashboardProps['onLogMeal'];
  selectedDate: string;
  isToday: boolean;
}) {
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
      <div className="card-header-with-badge">
        <h3>🔍 Log from Food Database</h3>
        <span className="pref-badge">Choose Your Own</span>
      </div>
      <p className="recommendations-intro">
        Search any food item or ingredient to log exact portions for {isToday ? 'today' : selectedDate}.
      </p>
      {message && <p className="form-error">{message}</p>}

      <form onSubmit={handleSubmit} className="log-meal-form">
        <div className="search-food-region">
          <label htmlFor="food-search-input" className="field-label">
            Search food
          </label>
          <input
            id="food-search-input"
            type="text"
            className="text-input"
            placeholder="e.g. Oatmeal, Dal Bhat, Apple…"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSelected(null);
            }}
            autoComplete="off"
          />

          {results.length > 0 && !selected && (
            <ul className="search-dropdown-list">
              {results.slice(0, 8).map((food) => (
                <li key={food.id}>
                  <button
                    type="button"
                    className="dropdown-item"
                    onClick={() => {
                      setSelected(food);
                      setQuery(food.name);
                      setResults([]);
                    }}
                  >
                    <span className="dropdown-food-name">{food.name}</span>
                    <span className="dropdown-food-meta">
                      {round(food.calories)} kcal • P: {food.protein}g C: {food.carbohydrates}g
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {selected && (
          <div className="selected-food-preview">
            <div>
              <strong>{selected.name}</strong>
              <div className="food-per-serving-hint">
                {round(selected.calories * quantity)} kcal (
                {round(selected.protein * quantity)}g P,{' '}
                {round(selected.carbohydrates * quantity)}g C,{' '}
                {round(selected.fat * quantity)}g F)
              </div>
            </div>
            <button
              type="button"
              className="btn-clear-selection"
              onClick={() => {
                setSelected(null);
                setQuery('');
              }}
            >
              Clear
            </button>
          </div>
        )}

        <div className="log-meal-row">
          <div className="field-group">
            <label htmlFor="meal-type-select" className="field-label">
              Meal type
            </label>
            <select
              id="meal-type-select"
              className="select-input"
              value={mealType}
              onChange={(event) => setMealType(event.target.value as MealType)}
            >
              {MEAL_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div className="field-group">
            <label htmlFor="meal-servings-input" className="field-label">
              Servings
            </label>
            <input
              id="meal-servings-input"
              type="number"
              min="0.25"
              max="20"
              step="0.25"
              className="text-input text-input-short"
              value={quantity}
              onChange={(event) => setQuantity(Math.max(0.25, Number(event.target.value) || 1))}
            />
          </div>
        </div>

        <button
          type="submit"
          className="btn-flat-primary btn-submit-meal"
          disabled={!selected || saving}
        >
          {saving ? 'Logging…' : `Log Meal for ${isToday ? 'Today' : selectedDate}`}
        </button>
      </form>
    </div>
  );
}

const CUISINE_OPTIONS = ['All', 'South Asian', 'East Asian', 'Western', 'Global'] as const;

function RecommendationsCard({
  profile,
  recommendations: initialRecommendations,
  loadingRecommendations: initialLoading,
  selectedDate,
  onLogMeal,
}: Pick<DashboardProps, 'profile' | 'recommendations' | 'loadingRecommendations' | 'selectedDate' | 'onLogMeal'>) {
  const [mealToLog, setMealToLog] = useState<ApiFood | null>(null);
  const [modalSlot, setModalSlot] = useState<MealType>(() => suggestedMealType());
  const [modalQuantity, setModalQuantity] = useState<number>(1);
  const [savingMeal, setSavingMeal] = useState(false);
  const [cuisineFilter, setCuisineFilter] = useState<string>('All');
  const [cuisineRecs, setCuisineRecs] = useState<ApiRecommendation[] | null>(null);
  const [loadingCuisine, setLoadingCuisine] = useState(false);

  // When cuisine filter changes to a specific region, query k-NN specifically within that cuisine
  useEffect(() => {
    if (cuisineFilter === 'All') {
      setCuisineRecs(null);
      return;
    }
    let cancelled = false;
    setLoadingCuisine(true);
    api
      .recommendations({ logDate: selectedDate, cuisine: cuisineFilter })
      .then((res) => {
        if (!cancelled) setCuisineRecs(res.recommendations);
      })
      .catch(() => {
        if (!cancelled) setCuisineRecs([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingCuisine(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDate, cuisineFilter]);

  const activeRecs = cuisineFilter === 'All' ? initialRecommendations : (cuisineRecs ?? []);
  const isLoading = cuisineFilter === 'All' ? initialLoading : loadingCuisine;

  return (
    <div className="dashboard-card recommendations-card">
      <div className="card-header-with-badge">
        <h3>✨ Tailored Meal Suggestions</h3>
        <span className="pref-badge">
          {profile?.dietary_preference && profile.dietary_preference !== 'None'
            ? `${profile.dietary_preference} • Tailored for You`
            : 'Tailored for You'}
        </span>
      </div>

      <p className="recommendations-intro">
        Smart food suggestions calculated to match your remaining calories and nutrients for today.
      </p>

      {/* Cuisine filter chips */}
      <div className="cuisine-filter-bar">
        <span className="cuisine-filter-label">Cuisine:</span>
        <div className="cuisine-chips-wrap">
          {CUISINE_OPTIONS.map((c) => (
            <button
              key={c}
              type="button"
              className={`cuisine-chip ${cuisineFilter === c ? 'active' : ''}`}
              onClick={() => setCuisineFilter(c)}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className="recommended-meals-list">
        {isLoading && (
          <p className="empty-logs-text">Loading {cuisineFilter !== 'All' ? `${cuisineFilter} ` : ''}recommendations…</p>
        )}

        {!isLoading && activeRecs.length === 0 && (
          <p className="empty-logs-text">
            No recommendations matching {cuisineFilter !== 'All' ? `the ${cuisineFilter} filter` : 'your profile'}.
          </p>
        )}

        {!isLoading &&
          activeRecs.map((food) => (
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
                  onClick={() => {
                    setMealToLog(food);
                    setModalSlot(suggestedMealType());
                    setModalQuantity(1);
                  }}
                  title={`Log ${food.name}`}
                >
                  + Log Meal
                </button>
              </div>

              {/* Explainable AI breakdown badges */}
              <div className="rec-xai-row">
                <span className="xai-chip match-chip">
                  🎯 {Math.round(food.similarity_score * 100)}% match
                </span>
                {food.protein >= 15 && (
                  <span className="xai-chip protein-chip">
                    ⚡ High Protein (+{round(food.protein)}g)
                  </span>
                )}
                {food.fiber >= 3 && (
                  <span className="xai-chip fiber-chip">
                    🌾 Fiber Rich (+{round(food.fiber)}g)
                  </span>
                )}
                {food.is_vegan ? (
                  <span className="xai-chip vegan-chip">🌿 Vegan</span>
                ) : food.is_vegetarian ? (
                  <span className="xai-chip veg-chip">🥛 Vegetarian</span>
                ) : null}
              </div>

              <div className="rec-macros-row">
                <span className="rec-macro-pill cal-pill">{round(food.calories)} kcal</span>
                <span className="rec-macro-pill prot-pill">P: {food.protein}g</span>
                <span className="rec-macro-pill carb-pill">C: {food.carbohydrates}g</span>
                <span className="rec-macro-pill fat-pill">F: {food.fat}g</span>
                <span className="rec-macro-pill fib-pill">Fib: {food.fiber}g</span>
              </div>
            </div>
          ))}
      </div>

      {/* Modal asking for meal slot and quantity after clicking Log Meal */}
      {mealToLog && (
        <div
          className="modal-overlay"
          onClick={() => {
            if (!savingMeal) setMealToLog(null);
          }}
          role="dialog"
          aria-modal="true"
        >
          <div className="modal-box log-recommendation-modal" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="modal-close"
              onClick={() => setMealToLog(null)}
              disabled={savingMeal}
              aria-label="Close"
            >
              ×
            </button>

            <div className="log-rec-modal-header">
              <span className="log-rec-modal-badge">{mealToLog.region}</span>
              <h3 className="log-rec-modal-title">Log {mealToLog.name}</h3>
              <p className="log-rec-modal-portion">Standard portion: {mealToLog.serving_size}</p>
            </div>

            <div className="log-rec-modal-form">
              <div className="form-field-group">
                <label className="field-label">Select Meal Slot:</label>
                <div className="log-rec-slot-chips">
                  {MEAL_TYPES.map((type) => (
                    <button
                      key={type}
                      type="button"
                      className={`log-rec-slot-chip ${modalSlot === type ? 'active' : ''}`}
                      onClick={() => setModalSlot(type)}
                      disabled={savingMeal}
                    >
                      {type === 'Breakfast'
                        ? '🌅 Breakfast'
                        : type === 'Lunch'
                        ? '☀️ Lunch'
                        : type === 'Dinner'
                        ? '🌙 Dinner'
                        : '🍎 Snack'}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-field-group">
                <label htmlFor="rec-modal-qty" className="field-label">Quantity / Servings:</label>
                <div className="log-rec-qty-stepper">
                  <button
                    type="button"
                    className="btn-stepper"
                    disabled={modalQuantity <= 0.5 || savingMeal}
                    onClick={() => setModalQuantity((q) => Math.max(0.5, Math.round((q - 0.5) * 10) / 10))}
                  >
                    −
                  </button>
                  <input
                    id="rec-modal-qty"
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="10"
                    className="text-input log-rec-qty-input"
                    value={modalQuantity}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      if (!isNaN(val) && val > 0) setModalQuantity(val);
                    }}
                    disabled={savingMeal}
                  />
                  <button
                    type="button"
                    className="btn-stepper"
                    disabled={modalQuantity >= 10 || savingMeal}
                    onClick={() => setModalQuantity((q) => Math.min(10, Math.round((q + 0.5) * 10) / 10))}
                  >
                    +
                  </button>
                </div>
              </div>

              <div className="log-rec-macro-preview">
                <div className="rec-preview-col">
                  <span className="rec-preview-val">{Math.round(mealToLog.calories * modalQuantity)}</span>
                  <span className="rec-preview-lbl">kcal</span>
                </div>
                <div className="rec-preview-col">
                  <span className="rec-preview-val">{round(mealToLog.protein * modalQuantity)}g</span>
                  <span className="rec-preview-lbl">Protein</span>
                </div>
                <div className="rec-preview-col">
                  <span className="rec-preview-val">{round(mealToLog.carbohydrates * modalQuantity)}g</span>
                  <span className="rec-preview-lbl">Carbs</span>
                </div>
                <div className="rec-preview-col">
                  <span className="rec-preview-val">{round(mealToLog.fat * modalQuantity)}g</span>
                  <span className="rec-preview-lbl">Fat</span>
                </div>
                <div className="rec-preview-col">
                  <span className="rec-preview-val">{round(mealToLog.fiber * modalQuantity)}g</span>
                  <span className="rec-preview-lbl">Fiber</span>
                </div>
              </div>

              <div className="log-rec-modal-actions">
                <button
                  type="button"
                  className="btn-flat-secondary"
                  onClick={() => setMealToLog(null)}
                  disabled={savingMeal}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-flat-primary"
                  disabled={savingMeal}
                  onClick={async () => {
                    setSavingMeal(true);
                    try {
                      await onLogMeal(mealToLog, modalQuantity, modalSlot);
                      setMealToLog(null);
                    } finally {
                      setSavingMeal(false);
                    }
                  }}
                >
                  {savingMeal ? 'Logging…' : `Log as ${modalSlot}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function Dashboard({
  profile,
  summary,
  recommendations,
  loadingRecommendations,
  history,
  loadingHistory,
  selectedDate,
  isToday,
  error,
  onPrevDay,
  onNextDay,
  onToday,
  onSelectDate,
  onLogMeal,
  onRemoveMeal,
}: DashboardProps) {
  const [showTrends, setShowTrends] = useState(false);

  const consumed = summary?.consumed ?? { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 };
  const targets = summary?.targets ?? { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 };
  const meals = summary?.meals ?? [];

  const calDiff = targets.calories - consumed.calories;

  return (
    <div className="dashboard-content-wrapper">
      {/* Date Navigation Bar */}
      <DateNavigator
        selectedDate={selectedDate}
        isToday={isToday}
        onPrevDay={onPrevDay}
        onNextDay={onNextDay}
        onToday={onToday}
        onSelectDate={onSelectDate}
      />

      <div className="dashboard-grid">
        <div className="dashboard-left">
          {/* Health Profile Card */}
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
              <p>
                <strong>Goal:</strong> {profile?.fitness_goal ?? 'Not set'}
              </p>
              <p>
                <strong>Preference:</strong> {profile?.dietary_preference ?? 'Not set'}
              </p>
              <p>
                <strong>Activity Level:</strong> {profile?.activity_level ?? 'Not set'}
              </p>
            </div>
          </div>

          {/* Daily Consumption Progress Card */}
          <div className="dashboard-card progress-card">
            <div className="card-header-with-badge">
              <h3>{isToday ? "Today's" : `${selectedDate}`} Progress</h3>
              <span className={`status-pill ${calDiff >= 0 ? 'status-ok' : 'status-over'}`}>
                {calDiff >= 0
                  ? `${round(calDiff)} kcal remaining`
                  : `${round(Math.abs(calDiff))} kcal over target`}
              </span>
            </div>

            {error && <p className="form-error">{error}</p>}

            <div className="metric-progress-wrapper">
              <div className="metric-header">
                <span>Calories</span>
                <span>
                  {round(consumed.calories)} / {round(targets.calories)} kcal
                </span>
              </div>
              <div className="progress-bar-bg">
                <div
                  className="progress-bar-fill cal-fill"
                  style={{ width: `${percent(consumed.calories, targets.calories)}%` }}
                />
              </div>
            </div>

            <div className="macros-progress-grid macros-4col">
              <MacroBar
                label="Protein"
                consumed={consumed.protein}
                target={targets.protein}
                className="prot-fill"
              />
              <MacroBar
                label="Carbs"
                consumed={consumed.carbs}
                target={targets.carbs}
                className="carb-fill"
              />
              <MacroBar
                label="Fat"
                consumed={consumed.fat}
                target={targets.fat}
                className="fat-fill"
              />
              <MacroBar
                label="Fiber"
                consumed={consumed.fiber}
                target={targets.fiber}
                className="fib-fill"
              />
            </div>

            <div className="trends-toggle-wrap">
              <button
                type="button"
                className="btn-toggle-trends"
                onClick={() => setShowTrends((val) => !val)}
              >
                {showTrends ? 'Hide 7-Day Analytics ▲' : 'Show 7-Day Nutrition Analytics ▼'}
              </button>
            </div>
          </div>

          {/* Expandable 7-Day Trends Chart */}
          {showTrends && <WeeklyTrendsChart history={history} loading={loadingHistory} />}

          {/* Log Meal Card */}
          <LogMealCard
            onLogMeal={onLogMeal}
            selectedDate={selectedDate}
            isToday={isToday}
          />
        </div>

        <div className="dashboard-right">
          {/* Recommendations Card */}
          <RecommendationsCard
            profile={profile}
            recommendations={recommendations}
            loadingRecommendations={loadingRecommendations}
            selectedDate={selectedDate}
            onLogMeal={onLogMeal}
          />

          {/* Meal Log List */}
          <div className="dashboard-card meal-history-card">
            <div className="card-header-with-badge">
              <h3>{isToday ? "Today's" : `${selectedDate}`} Meal Log</h3>
              <span className="meal-count-badge">{meals.length} meal(s)</span>
            </div>

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
                      <span className="meal-macro-pill cal-pill">{round(meal.calories)} kcal</span>
                      <button
                        className="btn-remove-meal"
                        onClick={() => void onRemoveMeal(meal.id)}
                        aria-label={`Remove ${meal.name}`}
                        title="Remove meal"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-logs-text">
                No meals logged for {isToday ? 'today' : selectedDate} yet. Use the form above to
                track a meal.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
