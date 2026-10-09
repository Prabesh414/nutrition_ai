import { useState } from 'react';

import { api } from '../api/client';
import type { ApiQuickLogItem, MealInput, MealType } from '../api/types';
import { MEAL_TYPES } from '../api/types';

interface QuickLogAIModalProps {
  onClose: () => void;
  onBatchLog: (meals: MealInput[]) => Promise<void>;
  selectedDate: string;
  defaultMealType?: MealType;
}

export function QuickLogAIModal({
  onClose,
  onBatchLog,
  selectedDate,
  defaultMealType = 'Breakfast',
}: QuickLogAIModalProps) {
  const [text, setText] = useState('');
  const [mealSlot, setMealSlot] = useState<MealType>(defaultMealType);
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [parsedItems, setParsedItems] = useState<ApiQuickLogItem[]>([]);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    if (!text.trim()) return;
    try {
      setParsing(true);
      setError(null);
      const res = await api.quickLogAI(text, selectedDate, mealSlot);
      setParsedItems(res.parsed_items);
      setNote(res.summary_note || (res.source === 'llm' ? 'Parsed with AI Nutrition Model' : 'Matched against catalog'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse natural language log');
    } finally {
      setParsing(false);
    }
  };

  const handleRemoveItem = (index: number) => {
    setParsedItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleConfirmLog = async () => {
    if (parsedItems.length === 0) return;
    const meals: MealInput[] = parsedItems.map((item) => ({
      name: item.name,
      quantity: item.quantity,
      meal_type: item.meal_type,
      calories: item.calories,
      protein: item.protein,
      carbs: item.carbs,
      fat: item.fat,
      fiber: item.fiber,
      log_date: selectedDate,
    }));

    try {
      setSaving(true);
      await onBatchLog(meals);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log meals');
    } finally {
      setSaving(false);
    }
  };

  const totalCalories = parsedItems.reduce((acc, curr) => acc + curr.calories, 0);
  const totalProtein = parsedItems.reduce((acc, curr) => acc + curr.protein, 0);
  const totalCarbs = parsedItems.reduce((acc, curr) => acc + curr.carbs, 0);
  const totalFat = parsedItems.reduce((acc, curr) => acc + curr.fat, 0);

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-box quick-log-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <div className="quick-log-header">
          <span className="quick-log-badge">💬 Natural Language Quick Log</span>
          <h3 className="modal-title">Describe What You Ate</h3>
          <p className="modal-subtitle">
            Type your meal in plain English (e.g. <em>&quot;2 boiled eggs, 1 cup of oatmeal with honey, and a banana&quot;</em>)
          </p>
        </div>

        <div className="quick-log-input-section">
          <div className="form-field-group">
            <label className="field-label">Target Meal Slot:</label>
            <div className="quick-log-slot-chips">
              {MEAL_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  className={`log-rec-slot-chip ${mealSlot === type ? 'active' : ''}`}
                  onClick={() => setMealSlot(type)}
                  disabled={parsing || saving}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          <div className="form-field-group">
            <label htmlFor="quick-log-input" className="field-label">Meal Description:</label>
            <textarea
              id="quick-log-input"
              className="quick-log-textarea"
              rows={3}
              placeholder="e.g. 1 bowl of chicken fried rice with a side salad and green tea..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={parsing || saving}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  handleParse();
                }
              }}
            />
          </div>

          <button
            type="button"
            className="btn-parse-ai"
            disabled={parsing || !text.trim() || saving}
            onClick={handleParse}
          >
            {parsing ? 'Analyzing Foods with AI…' : '✨ Parse & Extract Foods'}
          </button>
        </div>

        {error && <div className="modal-error-box">{error}</div>}

        {parsedItems.length > 0 && (
          <div className="parsed-results-box">
            <div className="parsed-results-header">
              <h4>Extracted Food Items ({parsedItems.length})</h4>
              {note && <span className="parsed-note">{note}</span>}
            </div>

            <div className="parsed-items-list">
              {parsedItems.map((item, idx) => (
                <div key={idx} className="parsed-item-row">
                  <div className="parsed-item-info">
                    <strong>{item.name}</strong>
                    <span className="parsed-item-qty">
                      {item.quantity} portion(s) • {item.meal_type}
                    </span>
                  </div>
                  <div className="parsed-item-macros">
                    <span>{Math.round(item.calories)} kcal</span>
                    <span>P: {item.protein}g</span>
                    <span>C: {item.carbs}g</span>
                    <span>F: {item.fat}g</span>
                  </div>
                  <button
                    type="button"
                    className="btn-remove-parsed"
                    onClick={() => handleRemoveItem(idx)}
                    title="Remove item"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <div className="parsed-totals-summary">
              <span>
                Total: <strong>{Math.round(totalCalories)} kcal</strong> | P: {Math.round(totalProtein)}g | C: {Math.round(totalCarbs)}g | F: {Math.round(totalFat)}g
              </span>
            </div>

            <div className="quick-log-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={onClose}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary btn-confirm-quicklog"
                disabled={saving || parsedItems.length === 0}
                onClick={handleConfirmLog}
              >
                {saving ? 'Logging Meals…' : `✓ Confirm & Log ${parsedItems.length} Food(s)`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
