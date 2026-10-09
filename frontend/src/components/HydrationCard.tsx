import { useCallback, useEffect, useState } from 'react';

import { api } from '../api/client';
import type { ApiWaterSummary } from '../api/types';

interface HydrationCardProps {
  selectedDate: string;
  isToday: boolean;
}

export function HydrationCard({ selectedDate, isToday }: HydrationCardProps) {
  const [summary, setSummary] = useState<ApiWaterSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [logging, setLogging] = useState(false);
  const [customMl, setCustomMl] = useState<number>(300);
  const [showCustom, setShowCustom] = useState(false);
  const [showLogs, setShowLogs] = useState(false);

  const loadWater = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getWaterSummary(selectedDate);
      setSummary(data);
    } catch {
      // Non-fatal if water fails to load
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    void loadWater();
  }, [loadWater]);

  const handleAddWater = async (amount: number) => {
    if (logging) return;
    try {
      setLogging(true);
      await api.addWaterLog(amount, selectedDate);
      await loadWater();
    } catch {
      // Handled gracefully
    } finally {
      setLogging(false);
      setShowCustom(false);
    }
  };

  const handleDeleteLog = async (id: number) => {
    try {
      await api.deleteWaterLog(id);
      await loadWater();
    } catch {
      // Handled gracefully
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset water logged for this day?')) return;
    try {
      await api.resetWaterDay(selectedDate);
      await loadWater();
    } catch {
      // Handled gracefully
    }
  };

  const totalMl = summary?.total_ml ?? 0;
  const targetMl = summary?.target_ml ?? 2500;
  const progressPct = summary?.progress_pct ?? Math.min(100, Math.round((totalMl / targetMl) * 100));
  const glasses = Math.round((totalMl / 250) * 10) / 10;

  return (
    <div className="hydration-card dash-card">
      <div className="card-header-row">
        <div>
          <h2 className="dash-card-title">💧 Daily Hydration Tracker</h2>
          <p className="card-subtitle">
            {isToday ? "Today's fluid intake & hydration goal" : `Fluid intake on ${selectedDate}`}
          </p>
        </div>
        {summary && summary.logs.length > 0 && (
          <button
            type="button"
            className="btn-text-action"
            onClick={handleReset}
            title="Reset water intake for this day"
          >
            ↺ Reset
          </button>
        )}
      </div>

      <div className="hydration-body">
        {/* Visual Water Gauge */}
        <div className="hydration-visual-wrap">
          <div className="water-glass">
            <div
              className="water-fill"
              style={{ height: `${Math.min(100, progressPct)}%` }}
            >
              <div className="water-wave" />
            </div>
            <div className="water-glass-overlay">
              <span className="water-pct-text">{progressPct}%</span>
            </div>
          </div>

          <div className="hydration-stats">
            <div className="hydration-metric-main">
              <span className="hydration-current-num">{totalMl.toLocaleString()}</span>
              <span className="hydration-target-unit"> / {targetMl.toLocaleString()} ml</span>
            </div>
            <p className="hydration-glasses-text">
              Approx. <strong>{glasses}</strong> standard glasses (250 ml each)
            </p>
            <div className="hydration-status-badge">
              {progressPct >= 100 ? (
                <span className="badge-hydrated">🎉 Hydration Goal Achieved!</span>
              ) : (
                <span className="badge-pending">
                  {(targetMl - totalMl).toLocaleString()} ml to reach your daily goal
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Quick Log Buttons */}
        <div className="hydration-quick-actions">
          <span className="quick-action-label">Quick Add:</span>
          <div className="quick-btn-row">
            <button
              type="button"
              className="btn-water-quick"
              disabled={logging || loading}
              onClick={() => handleAddWater(250)}
            >
              +250 ml <span>(Cup)</span>
            </button>
            <button
              type="button"
              className="btn-water-quick"
              disabled={logging || loading}
              onClick={() => handleAddWater(500)}
            >
              +500 ml <span>(Bottle)</span>
            </button>
            <button
              type="button"
              className="btn-water-quick"
              disabled={logging || loading}
              onClick={() => handleAddWater(750)}
            >
              +750 ml <span>(Large)</span>
            </button>
            <button
              type="button"
              className="btn-water-quick custom-toggle"
              disabled={loading}
              onClick={() => setShowCustom((s) => !s)}
            >
              + Custom
            </button>
          </div>
        </div>

        {/* Custom Input */}
        {showCustom && (
          <div className="hydration-custom-form">
            <label htmlFor="custom-water-ml" className="field-label">Custom amount (ml):</label>
            <div className="custom-input-row">
              <input
                id="custom-water-ml"
                type="number"
                min="50"
                max="3000"
                step="50"
                value={customMl}
                onChange={(e) => setCustomMl(Math.max(50, Number(e.target.value)))}
                className="input-water-custom"
              />
              <button
                type="button"
                className="btn-save-water"
                disabled={logging || customMl <= 0}
                onClick={() => handleAddWater(customMl)}
              >
                Log {customMl} ml
              </button>
            </div>
          </div>
        )}

        {/* Logs Accordion */}
        {summary && summary.logs.length > 0 && (
          <div className="hydration-logs-accordion">
            <button
              type="button"
              className="btn-toggle-logs"
              onClick={() => setShowLogs((s) => !s)}
            >
              {showLogs ? '▲ Hide today’s entries' : `▼ View ${summary.logs.length} logged entries`}
            </button>

            {showLogs && (
              <ul className="water-entries-list">
                {summary.logs.map((log) => (
                  <li key={log.id} className="water-entry-item">
                    <span>💧 +{log.amount_ml} ml</span>
                    <button
                      type="button"
                      className="btn-del-water"
                      onClick={() => handleDeleteLog(log.id)}
                      title="Delete entry"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
