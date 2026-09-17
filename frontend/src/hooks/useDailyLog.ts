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
  ApiRecommendation,
  ApiRecommendationsResponse,
  MealInput,
} from '../api/types';

const EMPTY_TOTALS = { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 };

export interface DailyLog {
  summary: ApiDailySummary | null;
  recommendations: ApiRecommendation[];
  loadingRecommendations: boolean;
  error: string | null;
  addMeal: (input: MealInput) => Promise<void>;
  removeMeal: (mealId: number) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useDailyLog(enabled: boolean): DailyLog {
  const [summary, setSummary] = useState<ApiDailySummary | null>(null);
  const [recommendations, setRecommendations] = useState<ApiRecommendation[]>([]);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Monotonic request id. Recommendations are refetched after every log and
  // delete, so two in-flight requests can resolve out of order; without this
  // an older response can overwrite a newer one.
  const latestRequest = useRef(0);

  const loadSummary = useCallback(async () => {
    const result = await api.dailySummary(localDateString());
    setSummary(result);
    return result;
  }, []);

  const loadRecommendations = useCallback(async () => {
    const requestId = ++latestRequest.current;
    setLoadingRecommendations(true);
    try {
      const result: ApiRecommendationsResponse = await api.recommendations();
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

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setError(null);
    try {
      await loadSummary();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load your meals.');
    }
    await loadRecommendations();
  }, [enabled, loadSummary, loadRecommendations]);

  useEffect(() => {
    if (!enabled) {
      setSummary(null);
      setRecommendations([]);
      return;
    }
    void refresh();
  }, [enabled, refresh]);

  const addMeal = useCallback(
    async (input: MealInput) => {
      await api.addMeal({ log_date: localDateString(), ...input });
      await refresh();
    },
    [refresh],
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

  return {
    summary,
    recommendations,
    loadingRecommendations,
    error,
    addMeal,
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
