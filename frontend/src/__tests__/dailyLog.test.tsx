import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../api/client';
import { useDailyLog } from '../hooks/useDailyLog';
import type { ApiDailySummary, ApiRecommendationsResponse } from '../api/types';

const SUMMARY: ApiDailySummary = {
  log_date: '2026-09-16',
  consumed: { calories: 320, protein: 11, carbs: 54, fat: 6, fiber: 8 },
  targets: { calories: 2000, protein: 100, carbs: 250, fat: 65, fiber: 25 },
  remaining: { calories: 1680, protein: 89, carbs: 196, fat: 59, fiber: 17 },
  meals: [],
};

function recsWith(name: string): ApiRecommendationsResponse {
  return {
    daily_targets: { calories: 2000, protein_g: 100, carbs_g: 250, fat_g: 65, fiber_g: 25 },
    consumed_today: { calories: 320, protein_g: 11, carbs_g: 54, fat_g: 6, fiber_g: 8 },
    next_meal_targets: { calories: 500, protein_g: 30, carbs_g: 60, fat_g: 16, fiber_g: 7 },
    recommendations: [{
      id: 1, name, serving_size: '1 serving', region: 'Global', calories: 400, fat: 5,
      carbohydrates: 50, protein: 30, fiber: 8, sugars: 2,
      is_vegetarian: true, is_vegan: true, similarity_score: 0.9,
    }],
  };
}

describe('useDailyLog', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('loads nothing while logged out', () => {
    const summarySpy = vi.spyOn(api, 'dailySummary');
    renderHook(() => useDailyLog(false));
    expect(summarySpy).not.toHaveBeenCalled();
  });

  it('loads the summary and recommendations once enabled', async () => {
    vi.spyOn(api, 'dailySummary').mockResolvedValue(SUMMARY);
    vi.spyOn(api, 'recommendations').mockResolvedValue(recsWith('Soy Flour'));

    const { result } = renderHook(() => useDailyLog(true));

    await waitFor(() => expect(result.current.summary).not.toBeNull());
    expect(result.current.summary?.consumed.calories).toBe(320);
    expect(result.current.recommendations[0].name).toBe('Soy Flour');
  });

  it('discards a stale recommendation response that resolves last', async () => {
    vi.spyOn(api, 'dailySummary').mockResolvedValue(SUMMARY);

    let releaseSlow: (value: ApiRecommendationsResponse) => void = () => {};
    const slow = new Promise<ApiRecommendationsResponse>((resolve) => { releaseSlow = resolve; });

    vi.spyOn(api, 'recommendations')
      .mockImplementationOnce(() => slow)
      .mockImplementationOnce(() => Promise.resolve(recsWith('NEWER')));

    const { result } = renderHook(() => useDailyLog(true));

    // Fire a second refresh, then let the *first* request finish afterwards.
    await act(async () => { await result.current.refresh(); });
    await waitFor(() => expect(result.current.recommendations[0]?.name).toBe('NEWER'));

    await act(async () => { releaseSlow(recsWith('STALE')); await slow; });

    expect(result.current.recommendations[0].name).toBe('NEWER');
  });

  it('propagates a delete failure instead of removing the meal locally', async () => {
    vi.spyOn(api, 'dailySummary').mockResolvedValue(SUMMARY);
    vi.spyOn(api, 'recommendations').mockResolvedValue(recsWith('Soy Flour'));
    vi.spyOn(api, 'deleteMeal').mockRejectedValue(new Error('Meal not found'));

    const { result } = renderHook(() => useDailyLog(true));
    await waitFor(() => expect(result.current.summary).not.toBeNull());

    await expect(result.current.removeMeal(99)).rejects.toThrow('Meal not found');
  });
});
