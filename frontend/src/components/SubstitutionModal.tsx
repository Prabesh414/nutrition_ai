import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { ApiFood, ApiSubstitutionItem, MealType } from '../api/types';

interface SubstitutionModalProps {
  food: ApiFood;
  onClose: () => void;
  onLogSwap: (food: ApiFood, quantity: number, mealType: MealType) => Promise<void>;
  defaultMealType?: MealType;
}

export function SubstitutionModal({
  food,
  onClose,
  onLogSwap,
  defaultMealType = 'Breakfast',
}: SubstitutionModalProps) {
  const [substitutions, setSubstitutions] = useState<ApiSubstitutionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggingId, setLoggingId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    const fetchSubs = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getSubstitutions(food.id, 6);
        if (active) {
          setSubstitutions(data.substitutions);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to find substitutions');
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchSubs();
    return () => {
      active = false;
    };
  }, [food.id]);

  const handleLog = async (sub: ApiSubstitutionItem) => {
    try {
      setLoggingId(sub.food.id);
      await onLogSwap(sub.food, sub.serving_multiplier, defaultMealType);
      onClose();
    } catch {
      // Handled in parent
    } finally {
      setLoggingId(null);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-box substitution-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <div className="substitution-header">
          <span className="sub-tag-badge">Smart Food Swaps</span>
          <h3 className="modal-title">Healthy Alternatives for {food.name}</h3>
          <p className="modal-subtitle">
            Original: {Math.round(food.calories)} kcal | P: {food.protein}g | C: {food.carbohydrates}g | F: {food.fat}g ({food.serving_size})
          </p>
        </div>

        {loading && (
          <div className="modal-loading-box">
            <div className="spinner" />
            <p>Analyzing catalogue for equivalent nutrition & healthier alternatives…</p>
          </div>
        )}

        {error && <div className="modal-error-box">{error}</div>}

        {!loading && !error && substitutions.length === 0 && (
          <div className="empty-subs-box">
            <p>No suitable alternative swaps found for this item.</p>
          </div>
        )}

        {!loading && !error && substitutions.length > 0 && (
          <div className="substitutions-list">
            {substitutions.map((sub) => (
              <div key={sub.food.id} className="sub-item-card">
                <div className="sub-card-top">
                  <div>
                    <div className="sub-badge-row">
                      <span className="sub-match-score">
                        {Math.round(sub.match_score * 100)}% Match
                      </span>
                      <span className="sub-region-badge">{sub.food.region}</span>
                      {sub.food.is_vegan ? (
                        <span className="xai-chip vegan-chip">Vegan</span>
                      ) : sub.food.is_vegetarian ? (
                        <span className="xai-chip veg-chip">Vegetarian</span>
                      ) : null}
                    </div>
                    <h4 className="sub-food-name">{sub.food.name}</h4>
                    <span className="sub-serving-desc">
                      Suggested portion: <strong>{sub.adjusted_serving_size}</strong>
                    </span>
                  </div>

                  <button
                    type="button"
                    className="btn-log-swap"
                    disabled={loggingId === sub.food.id}
                    onClick={() => handleLog(sub)}
                  >
                    {loggingId === sub.food.id ? 'Logging…' : '+ Log This Swap'}
                  </button>
                </div>

                <p className="sub-reason-text">💡 {sub.reason}</p>

                <div className="sub-macro-comparison">
                  <div className="macro-chip-col">
                    <span className="m-label">Calories</span>
                    <span className="m-val">{Math.round(sub.adjusted_calories)} kcal</span>
                  </div>
                  <div className="macro-chip-col">
                    <span className="m-label">Protein</span>
                    <span className="m-val">{sub.adjusted_protein}g</span>
                  </div>
                  <div className="macro-chip-col">
                    <span className="m-label">Carbs</span>
                    <span className="m-val">{sub.adjusted_carbs}g</span>
                  </div>
                  <div className="macro-chip-col">
                    <span className="m-label">Fat</span>
                    <span className="m-val">{sub.adjusted_fat}g</span>
                  </div>
                  <div className="macro-chip-col">
                    <span className="m-label">Fiber</span>
                    <span className="m-val">{sub.adjusted_fiber}g</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
