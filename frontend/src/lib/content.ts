/** Static presentational content for the landing page and offline fallback. */

export interface DiscoveryInsight {
  headline: string;
  description: string;
  detail: string;
  statLabel: string;
  statValue: string;
}

export interface DiscoveryItem {
  title: string;
  label: string;
  insights: DiscoveryInsight[];
}

export interface FallbackFood {
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  category: string;
}

export const HERO_FOOD_IMAGES: string[] = [
  'https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=2000&q=85'
];

export const DISCOVERY_ITEMS: DiscoveryItem[] = [
  {
    title: 'Build a better breakfast',
    label: 'Everyday idea',
    insights: [
      { headline: 'Start with a breakfast that carries you.', description: 'Pair a familiar favorite with protein and fruit for a breakfast that keeps you going.', detail: 'Oats + Greek yogurt + berries', statLabel: 'Why it works', statValue: 'Steady energy' },
      { headline: 'Let color do some of the planning.', description: 'A colorful breakfast can be simple: start with one fruit, one satisfying base, and something you enjoy.', detail: 'Color is a useful cue', statLabel: 'Try this', statValue: 'Add one fruit' },
      { headline: 'The best breakfast fits your morning.', description: 'There is no perfect breakfast. The best one is the one that fits your morning and leaves you feeling ready.', detail: 'Make it work for you', statLabel: 'Good to remember', statValue: 'Keep it realistic' }
    ]
  },
  {
    title: 'The global plate',
    label: 'Food culture',
    insights: [
      { headline: 'Every culture has its own balance.', description: 'Explore how balanced meals show up around the world, from lentil dal to colorful grain bowls.', detail: 'Curiosity belongs at the table', statLabel: 'Worth exploring', statValue: 'New flavors' },
      { headline: 'There is inspiration in every tradition.', description: 'Many food traditions build meals around plants, grains, herbs, and shared dishes. There is inspiration everywhere.', detail: 'Look beyond the usual', statLabel: 'Food thought', statValue: 'Shared meals' },
      { headline: 'One new ingredient can open a door.', description: 'Trying a new ingredient is a small adventure, whether it comes from a market nearby or a kitchen far away.', detail: 'One ingredient can open a door', statLabel: 'Explore next', statValue: 'Stay curious' }
    ]
  },
  {
    title: 'Small swaps, real progress',
    label: 'Practical insight',
    insights: [
      { headline: 'Small changes have a long tail.', description: 'Tiny changes count. Add one more vegetable, drink some water, or make your next snack satisfying.', detail: 'Progress over perfection', statLabel: 'Good to remember', statValue: 'It all adds up' },
      { headline: 'Choose the next doable thing.', description: 'You do not have to change everything at once. One thoughtful choice can make the next one easier.', detail: 'Start with what feels doable', statLabel: 'A gentler approach', statValue: 'One step today' },
      { headline: 'Your experience is part of the data.', description: 'Notice what helps you feel good, then build from there. Nutrition is personal, not a competition.', detail: 'Your experience matters', statLabel: 'Keep in mind', statValue: 'Make it yours' }
    ]
  }
];

/** Used only when the food API is unreachable, so search still returns something. */
export const FALLBACK_FOODS: FallbackFood[] = [
  { name: 'Almonds (28g)', calories: 164, protein: 6, carbs: 6, fat: 14, category: 'Nuts & Seeds' },
  { name: 'Amaranth (1 cup cooked)', calories: 251, protein: 9, carbs: 46, fat: 4, category: 'Grains' },
  { name: 'Apple (1 medium)', calories: 95, protein: 0.5, carbs: 25, fat: 0.3, category: 'Fruit' },
  { name: 'Avocado (half)', calories: 160, protein: 2, carbs: 9, fat: 15, category: 'Fruit' },
  { name: 'Bajra Roti (1)', calories: 120, protein: 3, carbs: 22, fat: 2, category: 'Indian' },
  { name: 'Banana (1 medium)', calories: 105, protein: 1.3, carbs: 27, fat: 0.4, category: 'Fruit' },
  { name: 'Barley (1 cup cooked)', calories: 193, protein: 4, carbs: 44, fat: 0.7, category: 'Grains' },
  { name: 'Beef, lean (100g)', calories: 217, protein: 26, carbs: 0, fat: 12, category: 'Meat' },
  { name: 'Beetroot (1 cup)', calories: 58, protein: 2, carbs: 13, fat: 0.2, category: 'Vegetable' },
  { name: 'Black Beans (1 cup cooked)', calories: 227, protein: 15, carbs: 41, fat: 0.9, category: 'Legumes' },
  { name: 'Blueberries (1 cup)', calories: 84, protein: 1.1, carbs: 21, fat: 0.5, category: 'Fruit' },
  { name: 'Broccoli (1 cup)', calories: 55, protein: 3.7, carbs: 11, fat: 0.6, category: 'Vegetable' },
  { name: 'Buckwheat (1 cup cooked)', calories: 155, protein: 5.7, carbs: 33, fat: 1, category: 'Grains' },
  { name: 'Buttermilk (1 cup)', calories: 98, protein: 8, carbs: 12, fat: 2.2, category: 'Dairy' },
  { name: 'Carrot (1 medium)', calories: 25, protein: 0.6, carbs: 6, fat: 0.1, category: 'Vegetable' },
  { name: 'Cashews (28g)', calories: 157, protein: 5, carbs: 9, fat: 12, category: 'Nuts & Seeds' },
  { name: 'Chana Masala (1 cup)', calories: 280, protein: 12, carbs: 42, fat: 8, category: 'Indian' },
  { name: 'Chia Seeds (2 tbsp)', calories: 138, protein: 5, carbs: 12, fat: 9, category: 'Nuts & Seeds' },
  { name: 'Chicken Breast (100g)', calories: 165, protein: 31, carbs: 0, fat: 3.6, category: 'Poultry' },
  { name: 'Chicken Tikka (100g)', calories: 190, protein: 27, carbs: 4, fat: 7, category: 'Indian' },
  { name: 'Chickpeas (1 cup cooked)', calories: 269, protein: 15, carbs: 45, fat: 4, category: 'Legumes' },
  { name: 'Coconut Milk (1 cup)', calories: 445, protein: 5, carbs: 6, fat: 48, category: 'Cooking Staples' },
  { name: 'Corn (1 cup)', calories: 143, protein: 5, carbs: 31, fat: 2.2, category: 'Vegetable' },
  { name: 'Cottage Cheese (1 cup)', calories: 206, protein: 28, carbs: 8, fat: 9, category: 'Dairy' },
  { name: 'Cucumber (1 cup)', calories: 16, protein: 0.7, carbs: 4, fat: 0.1, category: 'Vegetable' },
  { name: 'Dates (3)', calories: 200, protein: 1.3, carbs: 54, fat: 0.1, category: 'Fruit' },
  { name: 'Edamame (1 cup)', calories: 188, protein: 18, carbs: 14, fat: 8, category: 'Legumes' },
  { name: 'Eggs (2 large)', calories: 140, protein: 12, carbs: 1, fat: 10, category: 'Breakfast' },
  { name: 'Eggplant Bharta (1 cup)', calories: 190, protein: 4, carbs: 20, fat: 10, category: 'Indian' },
  { name: 'Feta Cheese (28g)', calories: 75, protein: 4, carbs: 1, fat: 6, category: 'Dairy' },
  { name: 'Flaxseed (2 tbsp)', calories: 110, protein: 4, carbs: 6, fat: 9, category: 'Nuts & Seeds' },
  { name: 'Ghee (1 tsp)', calories: 45, protein: 0, carbs: 0, fat: 5, category: 'Cooking Staples' },
  { name: 'Greek Yogurt (150g)', calories: 120, protein: 15, carbs: 6, fat: 4, category: 'Dairy' },
  { name: 'Guava (1 medium)', calories: 112, protein: 4, carbs: 24, fat: 1.6, category: 'Fruit' },
  { name: 'Hummus (1/4 cup)', calories: 166, protein: 8, carbs: 14, fat: 10, category: 'Legumes' },
  { name: 'Idli (2)', calories: 120, protein: 4, carbs: 25, fat: 0.5, category: 'Indian' },
  { name: 'Jackfruit (1 cup)', calories: 155, protein: 2.4, carbs: 40, fat: 0.5, category: 'Fruit' },
  { name: 'Kale (1 cup)', calories: 33, protein: 2.9, carbs: 6, fat: 0.6, category: 'Vegetable' },
  { name: 'Kiwi (2)', calories: 84, protein: 1.6, carbs: 20, fat: 0.8, category: 'Fruit' },
  { name: 'Lentil Dal (1 cup)', calories: 230, protein: 18, carbs: 40, fat: 1, category: 'Indian' },
  { name: 'Lentils (1 cup cooked)', calories: 230, protein: 18, carbs: 40, fat: 0.8, category: 'Legumes' },
  { name: 'Mango (1 cup)', calories: 99, protein: 1.4, carbs: 25, fat: 0.6, category: 'Fruit' },
  { name: 'Millet (1 cup cooked)', calories: 207, protein: 6, carbs: 41, fat: 1.7, category: 'Grains' },
  { name: 'Moong Dal Chilla (2)', calories: 220, protein: 13, carbs: 32, fat: 5, category: 'Indian' },
  { name: 'Mushrooms (1 cup)', calories: 21, protein: 3, carbs: 3, fat: 0.3, category: 'Vegetable' },
  { name: 'Naan (1 small)', calories: 260, protein: 9, carbs: 45, fat: 5, category: 'Indian' },
  { name: 'Oatmeal (1 cup cooked)', calories: 150, protein: 5, carbs: 27, fat: 3, category: 'Breakfast' },
  { name: 'Okra (1 cup)', calories: 33, protein: 1.9, carbs: 7, fat: 0.2, category: 'Indian' },
  { name: 'Olives (10)', calories: 40, protein: 0.3, carbs: 1, fat: 4, category: 'Cooking Staples' },
  { name: 'Orange (1 medium)', calories: 62, protein: 1.2, carbs: 15, fat: 0.2, category: 'Fruit' },
  { name: 'Paneer (100g)', calories: 265, protein: 18, carbs: 6, fat: 20, category: 'Indian' },
  { name: 'Papaya (1 cup)', calories: 55, protein: 0.9, carbs: 14, fat: 0.2, category: 'Fruit' },
  { name: 'Peach (1 medium)', calories: 59, protein: 1.4, carbs: 14, fat: 0.4, category: 'Fruit' },
  { name: 'Peanut Butter (2 tbsp)', calories: 190, protein: 8, carbs: 7, fat: 16, category: 'Nuts & Seeds' },
  { name: 'Pears (1 medium)', calories: 101, protein: 0.6, carbs: 27, fat: 0.3, category: 'Fruit' },
  { name: 'Pistachios (28g)', calories: 159, protein: 6, carbs: 8, fat: 13, category: 'Nuts & Seeds' },
  { name: 'Pomegranate (1 cup)', calories: 144, protein: 3, carbs: 33, fat: 2, category: 'Fruit' },
  { name: 'Quinoa (1 cup cooked)', calories: 222, protein: 8, carbs: 39, fat: 3.6, category: 'Grains' },
  { name: 'Rajma Masala (1 cup)', calories: 260, protein: 13, carbs: 40, fat: 6, category: 'Indian' },
  { name: 'Raspberries (1 cup)', calories: 65, protein: 1.5, carbs: 15, fat: 0.8, category: 'Fruit' },
  { name: 'Red Rice (1 cup cooked)', calories: 216, protein: 5, carbs: 45, fat: 1.8, category: 'Grains' },
  { name: 'Rice, brown (1 cup cooked)', calories: 215, protein: 5, carbs: 45, fat: 1.6, category: 'Grains' },
  { name: 'Rice, white (1 cup cooked)', calories: 205, protein: 4.3, carbs: 45, fat: 0.4, category: 'Grains' },
  { name: 'Salmon (100g)', calories: 206, protein: 22, carbs: 0, fat: 13, category: 'Seafood' },
  { name: 'Sardines (100g)', calories: 208, protein: 25, carbs: 0, fat: 11, category: 'Seafood' },
  { name: 'Sesame Seeds (2 tbsp)', calories: 103, protein: 3, carbs: 4, fat: 9, category: 'Nuts & Seeds' },
  { name: 'Shrimp (100g)', calories: 99, protein: 24, carbs: 0.2, fat: 0.3, category: 'Seafood' },
  { name: 'Spinach (1 cup cooked)', calories: 41, protein: 5, carbs: 7, fat: 0.5, category: 'Vegetable' },
  { name: 'Sweet Potato (1 medium)', calories: 112, protein: 2, carbs: 26, fat: 0.1, category: 'Vegetable' },
  { name: 'Tempeh (100g)', calories: 195, protein: 19, carbs: 8, fat: 11, category: 'Plant Protein' },
  { name: 'Tofu, firm (100g)', calories: 144, protein: 17, carbs: 3, fat: 9, category: 'Plant Protein' },
  { name: 'Tomato (1 medium)', calories: 22, protein: 1.1, carbs: 5, fat: 0.2, category: 'Vegetable' },
  { name: 'Tuna (100g)', calories: 132, protein: 29, carbs: 0, fat: 1.3, category: 'Seafood' },
  { name: 'Turkey Breast (100g)', calories: 135, protein: 30, carbs: 0, fat: 1, category: 'Poultry' },
  { name: 'Upma (1 cup)', calories: 220, protein: 6, carbs: 35, fat: 7, category: 'Indian' },
  { name: 'Walnuts (28g)', calories: 185, protein: 4.3, carbs: 4, fat: 18.5, category: 'Nuts & Seeds' },
  { name: 'Watermelon (1 cup)', calories: 46, protein: 0.9, carbs: 12, fat: 0.2, category: 'Fruit' },
  { name: 'Whole Wheat Bread (2 slices)', calories: 160, protein: 8, carbs: 28, fat: 2, category: 'Grains' },
  { name: 'Yogurt, plain (1 cup)', calories: 149, protein: 9, carbs: 11, fat: 8, category: 'Dairy' },
  { name: 'Zucchini (1 cup)', calories: 21, protein: 1.5, carbs: 4, fat: 0.4, category: 'Vegetable' }
];

/** Rotates the highlighted insight once per day, deterministically. */
export function dailyInsightIndex(insightCount: number): number {
  const today = new Date();
  const dayNumber = Math.floor(
    Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) / 86400000,
  );
  return dayNumber % insightCount;
}
