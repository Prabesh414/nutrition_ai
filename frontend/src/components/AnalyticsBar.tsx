import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { ApiAnalyticsSummary } from '../api/types';

interface AnalyticsBarProps {
  onRefreshTrigger?: number;
}

export function AnalyticsBar({ onRefreshTrigger }: AnalyticsBarProps) {
  const [analytics, setAnalytics] = useState<ApiAnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportDays, setExportDays] = useState<number>(30);
  const [showExportMenu, setShowExportMenu] = useState(false);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const data = await api.getAnalytics(7);
      setAnalytics(data);
    } catch {
      // Non-fatal
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [onRefreshTrigger]);

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      setExporting(format);
      await api.downloadExport(format, exportDays);
      setShowExportMenu(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(null);
    }
  };

  const streak = analytics?.streak_days ?? 0;
  const score = analytics?.adherence_score_pct ?? 0;

  return (
    <div className="analytics-bar-card">
      <div className="analytics-metrics-left">
        {/* Streak Badge */}
        <div className={`analytics-metric-badge streak-badge ${streak > 0 ? 'active-streak' : ''}`}>
          <span className="analytics-icon">🔥</span>
          <div className="analytics-info">
            <span className="analytics-val">{streak} {streak === 1 ? 'Day' : 'Days'}</span>
            <span className="analytics-lbl">Logging Streak</span>
          </div>
        </div>

        {/* Adherence Score */}
        <div className="analytics-metric-badge adherence-badge">
          <span className="analytics-icon">🎯</span>
          <div className="analytics-info">
            <span className="analytics-val">{score > 0 ? `${score}%` : '—'}</span>
            <span className="analytics-lbl">Weekly Target Match</span>
          </div>
        </div>

        {/* Activity count */}
        {analytics && analytics.days_logged > 0 && (
          <div className="analytics-metric-badge stats-badge hide-mobile">
            <span className="analytics-icon">📊</span>
            <div className="analytics-info">
              <span className="analytics-val">{analytics.total_meals_logged} meals</span>
              <span className="analytics-lbl">{analytics.days_logged} active days (7d)</span>
            </div>
          </div>
        )}
      </div>

      {/* Export Dropdown / Actions */}
      <div className="analytics-export-wrap">
        <div className="export-dropdown-rel">
          <button
            type="button"
            className="btn-export-trigger"
            onClick={() => setShowExportMenu((s) => !s)}
            disabled={loading}
          >
            📥 Export Logs ▾
          </button>

          {showExportMenu && (
            <div className="export-dropdown-menu">
              <div className="export-menu-header">
                <span>Time Window:</span>
                <select
                  value={exportDays}
                  onChange={(e) => setExportDays(Number(e.target.value))}
                  className="export-select-days"
                >
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                  <option value={365}>Last 1 year</option>
                </select>
              </div>

              <button
                type="button"
                className="export-menu-item"
                disabled={exporting !== null}
                onClick={() => handleExport('csv')}
              >
                📄 Download CSV Spreadsheet
              </button>

              <button
                type="button"
                className="export-menu-item"
                disabled={exporting !== null}
                onClick={() => handleExport('json')}
              >
                💾 Download JSON Data
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
