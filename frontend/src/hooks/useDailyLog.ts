/**
 * Today's meal log, its totals and the recommendations derived from them.
 *
 * All figures come from the server, scoped to a single calendar day. The old
 * implementation mirrored the whole meal history into localStorage and summed
 * it as "today", so the dashboard was wrong from the second day onward.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { api, localDateString } from '../api/client';
import type {
  ApiDailySummary,
  ApiHistoryPoint,
  ApiRecommendation,
  ApiRecommendationsResponse,
  MealInput,
} from '../api/types';

const EMPTY_TOTALS = { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 };

export function shiftDate(dateStr: string, deltaDays: number): string {
  const parts = dateStr.split('-').map(Number);
  const year = parts[0] ?? 2026;
  const month = parts[1] ?? 1;
  const day = parts[2] ?? 1;
  const d = new Date(year, month - 1, day);
  d.setDate(d.getDate() + deltaDays);
  return localDateString(d);
}

export interface DailyLog {
  selectedDate: string;
  isToday: boolean;
  setSelectedDate: (date: string) => void;
  goToPreviousDay: () => void;
  goToNextDay: () => void;
  goToToday: () => void;
  summary: ApiDailySummary | null;
  recommendations: ApiRecommendation[];
  loadingRecommendations: boolean;
  history: ApiHistoryPoint[];
  loadingHistory: boolean;
  error: string | null;
  addMeal: (input: MealInput) => Promise<void>;
  batchAddMeals: (meals: MealInput[]) => Promise<void>;
  removeMeal: (mealId: number) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useDailyLog(enabled: boolean): DailyLog {
  const [selectedDate, setSelectedDate] = useState<string>(() => localDateString());
  const [summary, setSummary] = useState<ApiDailySummary | null>(null);
  const [recommendations, setRecommendations] = useState<ApiRecommendation[]>([]);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [history, setHistory] = useState<ApiHistoryPoint[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Monotonic request id. Recommendations are refetched after every log and
  // delete, so two in-flight requests can resolve out of order; without this
  // an older response can overwrite a newer one.
  const latestRequest = useRef(0);

  const loadSummary = useCallback(async (targetDate: string) => {
    const result = await api.dailySummary(targetDate);
    setSummary(result);
    return result;
  }, []);

  const loadRecommendations = useCallback(async (targetDate: string) => {
    const requestId = ++latestRequest.current;
    setLoadingRecommendations(true);
    try {
      const result: ApiRecommendationsResponse = await api.recommendations(targetDate);
      if (requestId !== latestRequest.current) return; // A newer request won.
      setRecommendations(result.recommendations);
    } catch (caught) {
      if (requestId === latestRequest.current) {
        setRecommendations([]);
        setError(caught instanceof Error ? caught.message : 'Could not load recommendations.');
      }
    } finally {
      if (requestId === latestRequest.current) setLoadingRecommendations(false);
    }
  }, []);

  const loadHistory = useCallback(async (targetDate: string) => {
    setLoadingHistory(true);
    try {
      const res = await api.mealHistory(7, targetDate);
      setHistory(res?.days ?? []);
    } catch {
      // Non-fatal fallback: history simply stays empty.
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setError(null);
    try {
      await loadSummary(selectedDate);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load your meals.');
    }
    await loadRecommendations(selectedDate);
    await loadHistory(selectedDate);
  }, [enabled, selectedDate, loadSummary, loadRecommendations, loadHistory]);

  useEffect(() => {
    if (!enabled) {
      setSummary(null);
      setRecommendations([]);
      setHistory([]);
      return;
    }
    void refresh();
  }, [enabled, selectedDate, refresh]);

  const addMeal = useCallback(
    async (input: MealInput) => {
      await api.addMeal({ log_date: selectedDate, ...input });
      await refresh();
    },
    [selectedDate, refresh],
  );

  const batchAddMeals = useCallback(
    async (meals: MealInput[]) => {
      const prepared = meals.map((m) => ({ log_date: selectedDate, ...m }));
      await api.addBatchMeals(prepared);
      await refresh();
    },
    [selectedDate, refresh],
  );

  const removeMeal = useCallback(
    async (mealId: number) => {
      // No optimistic removal: a rejected delete used to fall through to the
      // local fallback and drop the meal from the UI anyway.
      await api.deleteMeal(mealId);
      await refresh();
    },
    [refresh],
  );

  const isToday = selectedDate === localDateString();

  const goToPreviousDay = useCallback(() => {
    setSelectedDate((curr) => shiftDate(curr, -1));
  }, []);

  const goToNextDay = useCallback(() => {
    setSelectedDate((curr) => {
      const next = shiftDate(curr, 1);
      const today = localDateString();
      return next > today ? curr : next;
    });
  }, []);

  const goToToday = useCallback(() => {
    setSelectedDate(localDateString());
  }, []);

  return {
    selectedDate,
    isToday,
    setSelectedDate,
    goToPreviousDay,
    goToNextDay,
    goToToday,
    summary,
    recommendations,
    loadingRecommendations,
    history,
    loadingHistory,
    error,
    addMeal,
    batchAddMeals,
    removeMeal,
    refresh,
  };
}

export function totalsOf(summary: ApiDailySummary | null) {
  return summary?.consumed ?? EMPTY_TOTALS;
}

export function targetsOf(summary: ApiDailySummary | null) {
  return summary?.targets ?? EMPTY_TOTALS;
}
