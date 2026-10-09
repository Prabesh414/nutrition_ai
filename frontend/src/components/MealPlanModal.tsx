import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { ApiMealPlanResponse, ApiMealPlanSlot, MealInput } from '../api/types';

interface MealPlanModalProps {
  onClose: () => void;
  onBatchLog: (meals: MealInput[]) => Promise<void>;
  selectedDate: string;
}

const CUISINES = ['All', 'South Asian', 'East Asian', 'Western', 'Global'] as const;

export function MealPlanModal({ onClose, onBatchLog, selectedDate }: MealPlanModalProps) {
  const [cuisine, setCuisine] = useState<string>('All');
  const [plan, setPlan] = useState<ApiMealPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchPlan = async (selectedCuisine: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDailyMealPlan(selectedCuisine);
      setPlan(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate meal plan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlan(cuisine);
  }, [cuisine]);

  const handleLogAll = async () => {
    if (!plan) return;
    const mealsToLog: MealInput[] = [];
    for (const slot of plan.slots) {
      for (const item of slot.items) {
        mealsToLog.push({
          name: item.food.name,
          quantity: item.servings,
          meal_type: slot.meal_type,
          calories: item.calories,
          protein: item.protein,
          carbs: item.carbs,
          fat: item.fat,
          fiber: item.fiber,
          log_date: selectedDate,
        });
      }
    }

    try {
      setSaving(true);
      await onBatchLog(mealsToLog);
      setSuccessMsg(`Successfully logged ${mealsToLog.length} meals to ${selectedDate}!`);
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log meals');
    } finally {
      setSaving(false);
    }
  };

  const handleLogSlot = async (slot: ApiMealPlanSlot) => {
    const mealsToLog: MealInput[] = slot.items.map((item) => ({
      name: item.food.name,
      quantity: item.servings,
      meal_type: slot.meal_type,
      calories: item.calories,
      protein: item.protein,
      carbs: item.carbs,
      fat: item.fat,
      fiber: item.fiber,
      log_date: selectedDate,
    }));

    try {
      setSaving(true);
      await onBatchLog(mealsToLog);
      setSuccessMsg(`Logged ${slot.meal_type} to ${selectedDate}!`);
      setTimeout(() => setSuccessMsg(null), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log slot');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-box meal-plan-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <div className="meal-plan-header">
          <div className="plan-badge-pill">⚡ AI Full-Day Nutrition Plan</div>
          <h3 className="modal-title">Personalized Full-Day Meal Plan</h3>
          <p className="modal-subtitle">
            Calibrated to your daily calorie target & macro distribution across all 4 meal slots
          </p>
        </div>

        {/* Cuisine Selector */}
        <div className="meal-plan-cuisine-row">
          <span className="cuisine-lbl">Select Cuisine Focus:</span>
          <div className="cuisine-chips-wrap">
            {CUISINES.map((c) => (
              <button
                key={c}
                type="button"
                className={`cuisine-chip ${cuisine === c ? 'active' : ''}`}
                onClick={() => setCuisine(c)}
                disabled={loading || saving}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="modal-loading-box">
            <div className="spinner" />
            <p>Crafting balanced breakfast, lunch, dinner, and snacks for your goals…</p>
          </div>
        )}

        {error && <div className="modal-error-box">{error}</div>}
        {successMsg && <div className="modal-success-box">{successMsg}</div>}

        {!loading && plan && (
          <div className="meal-plan-content">
            {/* Target Overview banner */}
            <div className="plan-overview-banner">
              <div className="plan-metric-col">
                <span className="p-lbl">Target Calories</span>
                <span className="p-val">{Math.round(plan.target_calories)} kcal</span>
              </div>
              <div className="plan-metric-col">
                <span className="p-lbl">Plan Total</span>
                <span className="p-val">{Math.round(plan.total_calories)} kcal</span>
              </div>
              <div className="plan-metric-col">
                <span className="p-lbl">Protein</span>
                <span className="p-val">{Math.round(plan.total_protein)}g</span>
              </div>
              <div className="plan-metric-col">
                <span className="p-lbl">Carbs</span>
                <span className="p-val">{Math.round(plan.total_carbs)}g</span>
              </div>
              <div className="plan-metric-col">
                <span className="p-lbl">Fat</span>
                <span className="p-val">{Math.round(plan.total_fat)}g</span>
              </div>
              <div className="plan-metric-col adherence-highlight">
                <span className="p-lbl">Target Match</span>
                <span className="p-val">{plan.adherence_pct}%</span>
              </div>
            </div>

            {plan.ai_tips && (
              <div className="plan-ai-tip-box">
                <strong>🤖 Coach Tip:</strong> {plan.ai_tips}
              </div>
            )}

            {/* Slots Cards */}
            <div className="plan-slots-grid">
              {plan.slots.map((slot) => (
                <div key={slot.meal_type} className="plan-slot-card">
                  <div className="slot-card-header">
                    <div>
                      <h4 className="slot-title">{slot.meal_type}</h4>
                      <span className="slot-cal-sub">
                        {Math.round(slot.total_calories)} kcal (Target: {Math.round(slot.target_calories)} kcal)
                      </span>
                    </div>
                    <button
                      type="button"
                      className="btn-slot-log"
                      disabled={saving}
                      onClick={() => handleLogSlot(slot)}
                    >
                      + Log {slot.meal_type}
                    </button>
                  </div>

                  <div className="slot-items-list">
                    {slot.items.map((item) => (
                      <div key={item.food.id} className="slot-food-row">
                        <div>
                          <strong className="slot-food-name">{item.food.name}</strong>
                          <span className="slot-portion-text">Portion: {item.adjusted_serving}</span>
                        </div>
                        <div className="slot-food-macros">
                          <span>{Math.round(item.calories)} kcal</span>
                          <span>P: {item.protein}g</span>
                          <span>C: {item.carbs}g</span>
                          <span>F: {item.fat}g</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Footer Action */}
            <div className="plan-modal-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={onClose}
                disabled={saving}
              >
                Close
              </button>
              <button
                type="button"
                className="btn-primary btn-log-all-plan"
                disabled={saving}
                onClick={handleLogAll}
              >
                {saving ? 'Logging Plan…' : `⚡ Log All 4 Meals to ${selectedDate}`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
