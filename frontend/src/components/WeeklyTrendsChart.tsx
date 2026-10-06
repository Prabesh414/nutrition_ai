import { useState } from 'react';

import type { ApiHistoryPoint } from '../api/types';

interface WeeklyTrendsChartProps {
  history: ApiHistoryPoint[];
  loading: boolean;
}

function dayOfWeek(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year ?? 2026, (month ?? 1) - 1, day ?? 1);
  return d.toLocaleDateString('en-US', { weekday: 'short' });
}

export function WeeklyTrendsChart({ history, loading }: WeeklyTrendsChartProps) {
  const [hoveredDay, setHoveredDay] = useState<ApiHistoryPoint | null>(null);

  if (loading && history.length === 0) {
    return (
      <div className="dashboard-card weekly-trends-card">
        <h3>7-Day Intake Analytics</h3>
        <p className="empty-logs-text">Loading multi-day trends…</p>
      </div>
    );
  }

  if (history.length === 0) {
    return null;
  }

  // Compute metrics
  const totalCalories = history.reduce((acc, pt) => acc + pt.calories_consumed, 0);
  const totalMeals = history.reduce((acc, pt) => acc + pt.meal_count, 0);
  const activeDays = history.filter((pt) => pt.meal_count > 0).length || 1;
  const avgCalories = Math.round(totalCalories / activeDays);

  const targets = history.map((pt) => pt.calories_target);
  const defaultTarget = targets[targets.length - 1] ?? 2000;

  const maxCal = Math.max(
    defaultTarget * 1.35,
    ...history.map((pt) => pt.calories_consumed),
    1000,
  );

  const chartWidth = 380;
  const chartHeight = 175;
  const topPad = 32;
  const bottomPad = 28;
  const leftPad = 20;
  const rightPad = 20;
  const plotWidth = chartWidth - leftPad - rightPad;
  const plotHeight = chartHeight - topPad - bottomPad;
  const baselineY = topPad + plotHeight;

  const barWidth = 26;
  const count = history.length || 7;
  const spacing = (plotWidth - barWidth * count) / (count + 1);

  const targetY = baselineY - (defaultTarget / maxCal) * plotHeight;

  return (
    <div className="dashboard-card weekly-trends-card">
      <div className="card-header-with-badge">
        <h3>7-Day Nutrition Trends</h3>
        <span className="trend-stat-badge">{activeDays} active day(s)</span>
      </div>

      <div className="trends-quick-stats">
        <div className="trend-stat-item">
          <span className="trend-stat-lbl">Daily Avg</span>
          <strong className="trend-stat-val">{avgCalories} kcal</strong>
        </div>
        <div className="trend-stat-item">
          <span className="trend-stat-lbl">Target Goal</span>
          <strong className="trend-stat-val">{Math.round(defaultTarget)} kcal</strong>
        </div>
        <div className="trend-stat-item">
          <span className="trend-stat-lbl">Meals Logged</span>
          <strong className="trend-stat-val">{totalMeals} meals</strong>
        </div>
      </div>

      <div className="svg-chart-container">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="weekly-svg-chart"
          aria-label="7-Day calories intake chart"
        >
          {/* Target guideline drawn behind bars */}
          <line
            x1={leftPad}
            y1={targetY}
            x2={chartWidth - rightPad}
            y2={targetY}
            stroke="var(--rust)"
            strokeDasharray="4 3"
            strokeWidth="1.5"
            strokeOpacity="0.75"
          />

          {/* Target label indicator with clean background pill */}
          <g transform={`translate(${chartWidth - rightPad - 105}, ${Math.max(8, targetY - 18)})`}>
            <rect
              x="0"
              y="0"
              width="105"
              height="15"
              rx="4"
              fill="var(--warm-white)"
              stroke="var(--rust)"
              strokeWidth="1"
              strokeOpacity="0.6"
            />
            <text
              x="52.5"
              y="11"
              textAnchor="middle"
              fontSize="8.5"
              fill="var(--rust)"
              fontWeight="700"
              letterSpacing="0.02em"
            >
              Target: {Math.round(defaultTarget)} kcal
            </text>
          </g>

          {/* Day Bars */}
          {history.map((pt, index) => {
            const x = leftPad + spacing + index * (barWidth + spacing);
            const barH = (pt.calories_consumed / maxCal) * plotHeight;
            const y = baselineY - barH;
            const isHovered = hoveredDay?.date === pt.date;
            const isOverTarget = pt.calories_consumed > pt.calories_target;

            return (
              <g
                key={pt.date}
                className="chart-bar-group"
                onMouseEnter={() => setHoveredDay(pt)}
                onMouseLeave={() => setHoveredDay(null)}
                tabIndex={0}
                role="button"
                aria-label={`${pt.date}: ${Math.round(pt.calories_consumed)} kcal`}
              >
                {/* Background track */}
                <rect
                  x={x}
                  y={topPad}
                  width={barWidth}
                  height={plotHeight}
                  rx="6"
                  fill="rgba(217, 210, 197, 0.3)"
                />

                {/* Filled bar */}
                {barH > 0 && (
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={Math.max(4, barH)}
                    rx="6"
                    className={`svg-bar-rect ${
                      isOverTarget ? 'bar-over-target' : 'bar-normal'
                    } ${isHovered ? 'bar-hovered' : ''}`}
                  />
                )}

                {/* Day label */}
                <text
                  x={x + barWidth / 2}
                  y={baselineY + 18}
                  textAnchor="middle"
                  fontSize="10"
                  fill="var(--earth)"
                  fontWeight={isHovered ? '700' : '500'}
                >
                  {dayOfWeek(pt.date)}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Dynamic Tooltip */}
        {hoveredDay && (
          <div className="chart-tooltip-bubble">
            <strong>{hoveredDay.date}</strong>
            <div className="tooltip-row">
              <span>Calories:</span>
              <span>{Math.round(hoveredDay.calories_consumed)} / {Math.round(hoveredDay.calories_target)} kcal</span>
            </div>
            <div className="tooltip-macros">
              <span>P: {Math.round(hoveredDay.protein_g)}g</span>
              <span>C: {Math.round(hoveredDay.carbs_g)}g</span>
              <span>F: {Math.round(hoveredDay.fat_g)}g</span>
            </div>
            <span className="tooltip-count">{hoveredDay.meal_count} meal(s) logged</span>
          </div>
        )}
      </div>
    </div>
  );
}
