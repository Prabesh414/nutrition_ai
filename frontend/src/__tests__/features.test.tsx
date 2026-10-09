import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../api/client';
import { AnalyticsBar } from '../components/AnalyticsBar';
import { HydrationCard } from '../components/HydrationCard';
import { MealPlanModal } from '../components/MealPlanModal';
import { QuickLogAIModal } from '../components/QuickLogAIModal';
import { SubstitutionModal } from '../components/SubstitutionModal';
import type {
  ApiAnalyticsSummary,
  ApiFood,
  ApiMealPlanResponse,
  ApiQuickLogResponse,
  ApiSubstitutionResponse,
  ApiWaterSummary,
} from '../api/types';

const MOCK_WATER: ApiWaterSummary = {
  log_date: '2026-10-09',
  total_ml: 750,
  target_ml: 2500,
  progress_pct: 30,
  logs: [
    { id: 1, amount_ml: 250, log_date: '2026-10-09', logged_at: null },
    { id: 2, amount_ml: 500, log_date: '2026-10-09', logged_at: null },
  ],
};

const MOCK_ANALYTICS: ApiAnalyticsSummary = {
  period_days: 7,
  streak_days: 5,
  avg_calories: 1850,
  avg_protein_g: 110,
  avg_carbs_g: 220,
  avg_fat_g: 55,
  avg_fiber_g: 28,
  adherence_score_pct: 94.5,
  days_logged: 6,
  total_meals_logged: 18,
  total_water_ml: 12500,
};

const MOCK_FOOD: ApiFood = {
  id: 10,
  name: 'Boiled Egg',
  serving_size: '1 egg (50g)',
  region: 'Global',
  calories: 78,
  protein: 6.3,
  carbohydrates: 0.6,
  fat: 5.3,
  fiber: 0,
  sugars: 0.5,
  is_vegetarian: true,
  is_vegan: false,
};

const MOCK_SUBS: ApiSubstitutionResponse = {
  original_food_id: 10,
  original_food_name: 'Boiled Egg',
  substitutions: [
    {
      food: {
        id: 20,
        name: 'Tofu Scramble',
        serving_size: '100g',
        region: 'Global',
        calories: 85,
        protein: 8.0,
        carbohydrates: 2.0,
        fat: 4.8,
        fiber: 1.5,
        sugars: 0.5,
        is_vegetarian: true,
        is_vegan: true,
      },
      original_food_name: 'Boiled Egg',
      serving_multiplier: 1.0,
      adjusted_serving_size: '100g',
      adjusted_calories: 85,
      adjusted_protein: 8.0,
      adjusted_carbs: 2.0,
      adjusted_fat: 4.8,
      adjusted_fiber: 1.5,
      match_score: 0.92,
      reason: '100% plant-based / vegan, +1.7g more protein',
    },
  ],
};

const MOCK_PLAN: ApiMealPlanResponse = {
  target_calories: 2000,
  total_calories: 1950,
  total_protein: 120,
  total_carbs: 230,
  total_fat: 60,
  total_fiber: 28,
  adherence_pct: 97.5,
  slots: [
    {
      meal_type: 'Breakfast',
      target_calories: 500,
      total_calories: 480,
      total_protein: 25,
      total_carbs: 65,
      total_fat: 12,
      total_fiber: 8,
      items: [
        {
          food: MOCK_FOOD,
          servings: 2,
          adjusted_serving: '2x (1 egg)',
          calories: 156,
          protein: 12.6,
          carbs: 1.2,
          fat: 10.6,
          fiber: 0,
        },
      ],
    },
    {
      meal_type: 'Lunch',
      target_calories: 700,
      total_calories: 680,
      total_protein: 45,
      total_carbs: 80,
      total_fat: 20,
      total_fiber: 10,
      items: [],
    },
    {
      meal_type: 'Dinner',
      target_calories: 600,
      total_calories: 590,
      total_protein: 38,
      total_carbs: 60,
      total_fat: 22,
      total_fiber: 8,
      items: [],
    },
    {
      meal_type: 'Snack',
      target_calories: 200,
      total_calories: 200,
      total_protein: 12,
      total_carbs: 25,
      total_fat: 6,
      total_fiber: 2,
      items: [],
    },
  ],
  ai_tips: 'Balanced protein distribution across 4 slots.',
};

describe('Advanced Analytics & Features UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders hydration tracker and adds water log', async () => {
    vi.spyOn(api, 'getWaterSummary').mockResolvedValue(MOCK_WATER);
    const addSpy = vi.spyOn(api, 'addWaterLog').mockResolvedValue({
      id: 3,
      amount_ml: 250,
      log_date: '2026-10-09',
      logged_at: null,
    });

    render(<HydrationCard selectedDate="2026-10-09" isToday={true} />);

    await waitFor(() => {
      expect(screen.getByText('750')).toBeTruthy();
      expect(screen.getByText('30%')).toBeTruthy();
    });

    const addBtn = screen.getByRole('button', { name: /\+250 ml/i });
    await act(async () => {
      fireEvent.click(addBtn);
    });

    expect(addSpy).toHaveBeenCalledWith(250, '2026-10-09');
  });

  it('renders analytics streak and adherence score', async () => {
    vi.spyOn(api, 'getAnalytics').mockResolvedValue(MOCK_ANALYTICS);

    render(<AnalyticsBar onRefreshTrigger={1} />);

    await waitFor(() => {
      expect(screen.getByText('5 Days')).toBeTruthy();
      expect(screen.getByText('94.5%')).toBeTruthy();
    });
  });

  it('renders substitution modal with healthy swap options', async () => {
    vi.spyOn(api, 'getSubstitutions').mockResolvedValue(MOCK_SUBS);
    const onLogSwap = vi.fn().mockResolvedValue(undefined);

    render(
      <SubstitutionModal
        food={MOCK_FOOD}
        onClose={vi.fn()}
        onLogSwap={onLogSwap}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Tofu Scramble')).toBeTruthy();
      expect(screen.getByText(/92% Match/i)).toBeTruthy();
    });

    const logSwapBtn = screen.getByRole('button', { name: /\+ Log This Swap/i });
    await act(async () => {
      fireEvent.click(logSwapBtn);
    });

    expect(onLogSwap).toHaveBeenCalledWith(MOCK_SUBS.substitutions[0].food, 1.0, 'Breakfast');
  });

  it('renders meal plan modal and logs full day plan', async () => {
    vi.spyOn(api, 'getDailyMealPlan').mockResolvedValue(MOCK_PLAN);
    const onBatchLog = vi.fn().mockResolvedValue(undefined);

    render(
      <MealPlanModal
        selectedDate="2026-10-09"
        onClose={vi.fn()}
        onBatchLog={onBatchLog}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('97.5%')).toBeTruthy();
      expect(screen.getByText('Breakfast')).toBeTruthy();
    });

    const logAllBtn = screen.getByRole('button', { name: /⚡ Log All 4 Meals/i });
    await act(async () => {
      fireEvent.click(logAllBtn);
    });

    expect(onBatchLog).toHaveBeenCalled();
  });

  it('parses natural language meal in QuickLogAIModal', async () => {
    const mockQuickLog: ApiQuickLogResponse = {
      parsed_items: [
        {
          name: 'Boiled Egg',
          quantity: 2,
          meal_type: 'Breakfast',
          calories: 156,
          protein: 12.6,
          carbs: 1.2,
          fat: 10.6,
          fiber: 0,
          confidence: 1.0,
        },
      ],
      summary_note: 'Parsed with AI Nutrition Assistant',
      source: 'llm',
    };

    vi.spyOn(api, 'quickLogAI').mockResolvedValue(mockQuickLog);
    const onBatchLog = vi.fn().mockResolvedValue(undefined);

    render(
      <QuickLogAIModal
        selectedDate="2026-10-09"
        onClose={vi.fn()}
        onBatchLog={onBatchLog}
      />,
    );

    const textarea = screen.getByPlaceholderText(/e.g. 1 bowl of chicken fried rice/i);
    await act(async () => {
      fireEvent.change(textarea, { target: { value: '2 boiled eggs' } });
    });

    const parseBtn = screen.getByRole('button', { name: /✨ Parse & Extract Foods/i });
    await act(async () => {
      fireEvent.click(parseBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('Boiled Egg')).toBeTruthy();
      expect(screen.getAllByText(/156 kcal/i).length).toBeGreaterThan(0);
    });

    const confirmBtn = screen.getByRole('button', { name: /✓ Confirm & Log/i });
    await act(async () => {
      fireEvent.click(confirmBtn);
    });

    expect(onBatchLog).toHaveBeenCalledWith([
      expect.objectContaining({ name: 'Boiled Egg', quantity: 2, calories: 156 }),
    ]);
  });
});
