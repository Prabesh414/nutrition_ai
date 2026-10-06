import { useId } from 'react';

import { localDateString } from '../api/client';

interface DateNavigatorProps {
  selectedDate: string;
  isToday: boolean;
  onPrevDay: () => void;
  onNextDay: () => void;
  onToday: () => void;
  onSelectDate: (date: string) => void;
}

function formatDateLabel(dateStr: string, isToday: boolean): string {
  if (isToday) return 'Today';
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(year ?? 2026, (month ?? 1) - 1, day ?? 1);

  // Check if yesterday
  const now = new Date();
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }

  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

function formatFullDate(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(year ?? 2026, (month ?? 1) - 1, day ?? 1);
  return date.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

export function DateNavigator({
  selectedDate,
  isToday,
  onPrevDay,
  onNextDay,
  onToday,
  onSelectDate,
}: DateNavigatorProps) {
  const inputId = useId();
  const todayStr = localDateString();

  return (
    <div className="date-navigator-card">
      <div className="date-nav-controls">
        <button
          type="button"
          className="btn-date-nav btn-prev-day"
          onClick={onPrevDay}
          title="Previous day"
          aria-label="Previous day"
        >
          ‹
        </button>

        <div className="date-display-wrap">
          <label htmlFor={inputId} className="date-label-clickable" title="Click to choose a date">
            <span className="date-tag-badge">{formatDateLabel(selectedDate, isToday)}</span>
            <span className="date-full-text">{formatFullDate(selectedDate)}</span>
            <svg
              className="calendar-icon"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
          </label>
          <input
            id={inputId}
            type="date"
            className="date-picker-hidden"
            value={selectedDate}
            max={todayStr}
            onChange={(e) => {
              if (e.target.value) onSelectDate(e.target.value);
            }}
          />
        </div>

        <button
          type="button"
          className="btn-date-nav btn-next-day"
          onClick={onNextDay}
          disabled={isToday}
          title={isToday ? 'Cannot navigate into future' : 'Next day'}
          aria-label="Next day"
        >
          ›
        </button>
      </div>

      <div className="date-nav-actions">
        {!isToday && (
          <button type="button" className="btn-jump-today" onClick={onToday}>
            Back to Today
          </button>
        )}
        <span className={`date-status-indicator ${isToday ? 'status-live' : 'status-past'}`}>
          {isToday ? '● Live Day' : '○ Historical Log'}
        </span>
      </div>
    </div>
  );
}
