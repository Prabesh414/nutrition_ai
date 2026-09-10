import { useEffect, useState } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
const MOCK_FOODS = [
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

const HERO_FOOD_IMAGES = [
  'https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=2000&q=85',
  'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=2000&q=85'
];

const DISCOVERY_ITEMS = [
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

const getDailyInsightIndex = (insightCount: number) => {
  const today = new Date();
  const dayNumber = Math.floor(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) / 86400000);
  return dayNumber % insightCount;
};

interface HealthProfile {
  age: number;
  gender: 'Male' | 'Female';
  height: number;
  weight: number;
  activityLevel: 'Sedentary' | 'Lightly Active' | 'Moderately Active' | 'Very Active';
  fitnessGoal: 'Lose Weight' | 'Maintain Weight' | 'Gain Weight';
  dietaryPreference: 'None' | 'Vegetarian' | 'Vegan' | 'Keto';
  profileImageUrl?: string;
  bmi: number;
  bmr: number;
  targetCalories: number;
  targetProtein: number;
  targetCarbs: number;
  targetFat: number;
}

interface LoggedMeal {
  name: string;
  quantity: number;
  mealType: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

function mapBackendProfileToFrontend(profile: any): HealthProfile | null {
  if (!profile) return null;
  return {
    age: profile.age,
    gender: profile.gender,
    height: profile.height,
    weight: profile.weight,
    activityLevel: profile.activity_level,
    fitnessGoal: profile.fitness_goal,
    dietaryPreference: profile.dietary_preference,
    profileImageUrl: profile.profile_image_url || undefined,
    bmi: profile.bmi,
    bmr: profile.bmr,
    targetCalories: profile.target_calories,
    targetProtein: profile.target_protein,
    targetCarbs: profile.target_carbs,
    targetFat: profile.target_fat
  };
}

function mapBackendMealToFrontend(meal: any): LoggedMeal {
  return {
    name: meal.name,
    quantity: meal.quantity,
    mealType: meal.meal_type,
    calories: meal.calories,
    protein: meal.protein,
    carbs: meal.carbs,
    fat: meal.fat,
  };
}

function searchFoods(query: string): typeof MOCK_FOODS {
  if (!query.trim()) return [];
  return MOCK_FOODS.filter(food =>
    food.name.toLowerCase().includes(query.toLowerCase())
  );
}

function App() {
  // Navigation & Page Tab State
  const [activeSection, setActiveSection] = useState<'home' | 'search' | 'features'>('home');
  const [activeDashboardTab, setActiveDashboardTab] = useState<'overview' | 'coach'>('overview');
  const [showLandingPage, setShowLandingPage] = useState(false);

  // Search State
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<typeof MOCK_FOODS>([]);
  const [searched, setSearched] = useState(false);
  const [selectedDiscovery, setSelectedDiscovery] = useState(DISCOVERY_ITEMS[0]);
  const [selectedInsightIndex, setSelectedInsightIndex] = useState(getDailyInsightIndex(DISCOVERY_ITEMS[0].insights.length));
  const [heroImageIndex, setHeroImageIndex] = useState(0);

  // Authentication State
  const [user, setUser] = useState<{
    username?: string;
    firstName?: string;
    middleName?: string;
    lastName?: string;
    email: string;
    profile: HealthProfile | null;
  } | null>(null);
  const [activeModal, setActiveModal] = useState<'login' | 'signup' | 'profile' | null>(null);
  const [activeProfileView, setActiveProfileView] = useState<'dashboard' | 'profile'>('dashboard');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [usageEstimate, setUsageEstimate] = useState({ prompts: 0, tokens: 0 });
  const [uploadedProfileImage, setUploadedProfileImage] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setSelectedInsightIndex(index => (index + 1) % selectedDiscovery.insights.length);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [selectedDiscovery]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setHeroImageIndex(index => (index + 1) % HERO_FOOD_IMAGES.length);
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    return () => {
      if (uploadedProfileImage?.startsWith('blob:')) {
        URL.revokeObjectURL(uploadedProfileImage);
      }
    };
  }, [uploadedProfileImage]);

  // Form Fields
  const [authFirstName, setAuthFirstName] = useState('');
  const [authMiddleName, setAuthMiddleName] = useState('');
  const [authLastName, setAuthLastName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');

  // Profile Form Fields
  const [age, setAge] = useState<number>(25);
  const [gender, setGender] = useState<'Male' | 'Female'>('Male');
  const [height, setHeight] = useState<number>(175);
  const [weight, setWeight] = useState<number>(70);
  const [activity, setActivity] = useState<HealthProfile['activityLevel']>('Moderately Active');
  const [goal, setGoal] = useState<HealthProfile['fitnessGoal']>('Maintain Weight');
  const [diet, setDiet] = useState<HealthProfile['dietaryPreference']>('None');

  // Dashboard Tracker state
  const [trackedMeals, setTrackedMeals] = useState<LoggedMeal[]>([]);
  
  // Custom Food Log Input state
  const [logFoodQuery, setLogFoodQuery] = useState('');
  const [logFoodResults, setLogFoodResults] = useState<typeof MOCK_FOODS>([]);
  const [selectedFood, setSelectedFood] = useState<typeof MOCK_FOODS[0] | null>(null);
  const [mealQty, setMealQty] = useState(1);
  const [mealType, setMealType] = useState('Breakfast');

  // Chatbot state
  const [chatMessages, setChatMessages] = useState<{ sender: 'user' | 'coach'; text: string }[]>([
    { sender: 'coach', text: 'Hi! I am your AI Nutrition Coach. How can I help you reach your dietary goals today?' }
  ]);
  const [chatInput, setChatInput] = useState('');

  // Search logic on landing page
  const handleLandingSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setSearchResults([]);
      setSearched(false);
      return;
    }
    setSearchResults(searchFoods(query));
    setSearched(true);
  };

  // Auth actions
  const openLogin = () => {
    setAuthFirstName('');
    setAuthMiddleName('');
    setAuthLastName('');
    setAuthEmail('');
    setAuthPassword('');
    setActiveModal('login');
  };

  const openSignup = () => {
    setAuthFirstName('');
    setAuthMiddleName('');
    setAuthLastName('');
    setAuthEmail('');
    setAuthPassword('');
    setActiveModal('signup');
  };

  const handleLogoClick = () => {
    window.location.reload();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authEmail || !authPassword) return;

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });

      const data = await response.json();
      if (!response.ok) {
        alert(data.detail || 'Login failed');
        return;
      }

      const profile = mapBackendProfileToFrontend(data.profile);
      const meals = (data.meals || []).map(mapBackendMealToFrontend);

      setUser({
        username: data.username || undefined,
        firstName: data.first_name || undefined,
        middleName: data.middle_name || undefined,
        lastName: data.last_name || undefined,
        email: data.email,
        profile,
      });
      setShowLandingPage(false);
      setTrackedMeals(meals);
      setUploadedProfileImage(data.profile?.profile_image_url || null);
      setActiveModal(null);
      setActiveDashboardTab('overview');
    } catch (error) {
      console.error(error);
      alert('Unable to connect to backend. Start the FastAPI server first.');
    }
  };

  const handleSignupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (authFirstName && authLastName && authEmail && authPassword) {
      setActiveModal('profile');
    }
  };

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const heightInMeters = height / 100;
    const bmi = parseFloat((weight / (heightInMeters * heightInMeters)).toFixed(1));

    let bmr = 0;
    if (gender === 'Male') {
      bmr = 10 * weight + 6.25 * height - 5 * age + 5;
    } else {
      bmr = 10 * weight + 6.25 * height - 5 * age - 161;
    }
    bmr = Math.round(bmr);

    const activityMultipliers = {
      'Sedentary': 1.2,
      'Lightly Active': 1.375,
      'Moderately Active': 1.55,
      'Very Active': 1.725
    };
    const tdee = bmr * activityMultipliers[activity];

    let targetCalories = tdee;
    if (goal === 'Lose Weight') targetCalories -= 500;
    if (goal === 'Gain Weight') targetCalories += 500;
    targetCalories = Math.round(targetCalories);

    const targetProtein = Math.round((targetCalories * 0.25) / 4);
    const targetCarbs = Math.round((targetCalories * 0.50) / 4);
    const targetFat = Math.round((targetCalories * 0.25) / 9);

    try {
      const registerResponse = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: authFirstName,
          middle_name: authMiddleName || null,
          last_name: authLastName,
          email: authEmail,
          password: authPassword,
        })
      });

      const registerData = await registerResponse.json();
      if (!registerResponse.ok) {
        if (registerData.detail === 'User already exists') {
          alert('This email is already registered. Please log in instead.');
          setActiveModal('login');
          return;
        }
        alert(registerData.detail || 'Registration failed');
        return;
      }

      const profileResponse = await fetch(`${API_BASE_URL}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: authEmail,
          age,
          gender,
          height,
          weight,
          activity_level: activity,
          fitness_goal: goal,
          dietary_preference: diet,
          bmi,
          bmr,
          target_calories: targetCalories,
          target_protein: targetProtein,
          target_carbs: targetCarbs,
          target_fat: targetFat
        })
      });

      const profileData = await profileResponse.json();
      if (!profileResponse.ok) {
        alert(profileData.detail || 'Profile save failed');
        return;
      }

      setUser({
        firstName: authFirstName,
        middleName: authMiddleName || undefined,
        lastName: authLastName,
        email: authEmail,
        profile: mapBackendProfileToFrontend(profileData)
      });
      setShowLandingPage(false);

      if (profileData.profile_image_url) {
        setUploadedProfileImage(profileData.profile_image_url);
      }

      setActiveModal(null);
      setActiveDashboardTab('overview');
    } catch (error) {
      console.error(error);
      alert('Unable to connect to backend. Start the FastAPI server first.');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setTrackedMeals([]);
    setSelectedFood(null);
    setLogFoodQuery('');
    setLogFoodResults([]);
    setUsageEstimate({ prompts: 0, tokens: 0 });
    setUploadedProfileImage(null);
    setActiveSection('home');
    setActiveProfileView('dashboard');
  };

  const maleProfileAsset = new URL('./assets/png/male.png', import.meta.url).href;
  const femaleProfileAsset = new URL('./assets/png/woman.png', import.meta.url).href;

  const defaultProfileImage = user?.profile?.gender === 'Female'
    ? femaleProfileAsset
    : maleProfileAsset;

  const activeProfileImage = uploadedProfileImage || user?.profile?.profileImageUrl || defaultProfileImage;

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      alert('Please select a valid image file.');
      event.target.value = '';
      return;
    }

    const readAsDataUrl = new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(new Error('Could not read file'));
      reader.readAsDataURL(file);
    });

    try {
      const dataUrl = await readAsDataUrl;
      setUploadedProfileImage(dataUrl);

      if (!user) {
        event.target.value = '';
        return;
      }

      const currentProfile = user.profile ?? {
        age,
        gender,
        height,
        weight,
        activityLevel: activity,
        fitnessGoal: goal,
        dietaryPreference: diet,
        bmi: 0,
        bmr: 0,
        targetCalories: 0,
        targetProtein: 0,
        targetCarbs: 0,
        targetFat: 0
      };

      const payload = {
        email: user.email,
        age: currentProfile.age,
        gender: currentProfile.gender,
        height: currentProfile.height,
        weight: currentProfile.weight,
        activity_level: currentProfile.activityLevel,
        fitness_goal: currentProfile.fitnessGoal,
        dietary_preference: currentProfile.dietaryPreference,
        profile_image_url: dataUrl,
        bmi: currentProfile.bmi,
        bmr: currentProfile.bmr,
        target_calories: currentProfile.targetCalories,
        target_protein: currentProfile.targetProtein,
        target_carbs: currentProfile.targetCarbs,
        target_fat: currentProfile.targetFat
      };

      const response = await fetch(`${API_BASE_URL}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const savedProfile = await response.json();
      if (!response.ok) {
        alert(savedProfile.detail || 'Could not save profile image.');
        return;
      }

      setUser(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          profile: mapBackendProfileToFrontend(savedProfile)
        };
      });
    } catch (error) {
      console.error(error);
      alert('Unable to save your profile picture.');
    }

    event.target.value = '';
  };

  // Log meals logic
  const handleLogFoodSearch = (val: string) => {
    setLogFoodQuery(val);
    setLogFoodResults(searchFoods(val));
  };

  const handleSelectFoodToLog = (food: typeof MOCK_FOODS[0]) => {
    setSelectedFood(food);
    setLogFoodQuery(food.name);
    setLogFoodResults([]);
  };

  const handleLogMealSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFood || !user) return;

    const newLog: LoggedMeal = {
      name: selectedFood.name,
      quantity: mealQty,
      mealType,
      calories: Math.round(selectedFood.calories * mealQty),
      protein: Math.round(selectedFood.protein * mealQty),
      carbs: Math.round(selectedFood.carbs * mealQty),
      fat: Math.round(selectedFood.fat * mealQty)
    };

    try {
      const response = await fetch(`${API_BASE_URL}/meals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: user.email,
          name: newLog.name,
          quantity: newLog.quantity,
          meal_type: newLog.mealType,
          calories: newLog.calories,
          protein: newLog.protein,
          carbs: newLog.carbs,
          fat: newLog.fat
        })
      });

      const mealsData = await response.json();
      if (!response.ok) {
        alert(mealsData.detail || 'Unable to save meal.');
        return;
      }

      setTrackedMeals(mealsData.map(mapBackendMealToFrontend));
      setUsageEstimate(prev => ({ prompts: prev.prompts + 1, tokens: prev.tokens + 50 }));
      setSelectedFood(null);
      setLogFoodQuery('');
      setMealQty(1);
    } catch (error) {
      console.error(error);
      alert('Unable to save meal. Start the backend server first.');
    }
  };

  const handleRemoveLoggedMeal = (idx: number) => {
    setTrackedMeals(trackedMeals.filter((_, i) => i !== idx));
  };

  // Chatbot logic
  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setChatMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setChatInput('');
    setUsageEstimate(prev => ({ prompts: prev.prompts + 1, tokens: prev.tokens + 120 }));

    setTimeout(() => {
      let reply = "That's an interesting question. Remember to stay hydrated and balance your macronutrients!";
      const lower = userMsg.toLowerCase();

      if (lower.includes('water') || lower.includes('hydrate')) {
        reply = "Hydration is essential! Try to drink at least 2.5 to 3 liters of water daily, especially if you are active.";
      } else if (lower.includes('protein')) {
        if (user?.profile) {
          reply = `Based on your goal to ${user.profile.fitnessGoal.toLowerCase()}, your daily target is ${user.profile.targetProtein}g of protein. Excellent sources include chicken breast, salmon, eggs, and tofu.`;
        } else {
          reply = "Protein is vital for muscle repair. Aim for lean meats, fish, eggs, dairy, or plant-based legumes.";
        }
      } else if (lower.includes('bmr') || lower.includes('bmi')) {
        if (user?.profile) {
          reply = `Your BMR (Basal Metabolic Rate) is ${user.profile.bmr} kcal. This is the energy your body needs to function at rest. Your current BMI is ${user.profile.bmi}.`;
        }
      } else if (lower.includes('calories') || lower.includes('eat')) {
        const totalCals = trackedMeals.reduce((acc, curr) => acc + curr.calories, 0);
        if (user?.profile) {
          const remaining = user.profile.targetCalories - totalCals;
          reply = `You have consumed ${totalCals} kcal today out of your ${user.profile.targetCalories} kcal budget. You have ${remaining > 0 ? remaining : 0} kcal remaining today.`;
        }
      }

      setChatMessages(prev => [...prev, { sender: 'coach', text: reply }]);
    }, 800);
  };

  const totalCals = trackedMeals.reduce((acc, curr) => acc + curr.calories, 0);
  const totalProtein = trackedMeals.reduce((acc, curr) => acc + curr.protein, 0);
  const totalCarbs = trackedMeals.reduce((acc, curr) => acc + curr.carbs, 0);
  const totalFat = trackedMeals.reduce((acc, curr) => acc + curr.fat, 0);

  return (
    <div className="landing-wrapper">
      
      {/* GLOBAL PERSISTENT HEADER NAVBAR */}
      <header className="navbar">
        <button className="brand" type="button" onClick={handleLogoClick} aria-label="Refresh NutritionAI home page">
          Nutrition<span className="brand-dot">AI</span>
        </button>
        
        <nav className="nav-links">
          {!user ? (
            <>
              <span 
                className={`nav-link ${activeSection === 'home' ? 'active' : ''}`}
                onClick={() => setActiveSection('home')}
                style={{ cursor: 'pointer' }}
              >
                Home
              </span>
              <span 
                className={`nav-link ${activeSection === 'search' ? 'active' : ''}`}
                onClick={() => setActiveSection('search')}
                style={{ cursor: 'pointer' }}
              >
                Search Food
              </span>
              <span 
                className={`nav-link ${activeSection === 'features' ? 'active' : ''}`}
                onClick={() => setActiveSection('features')}
                style={{ cursor: 'pointer' }}
              >
                Features
              </span>
            </>
          ) : (
            <>
              <span 
                className={`nav-link ${activeDashboardTab === 'overview' ? 'active' : ''}`}
                onClick={() => {
                  setShowLandingPage(false);
                  setActiveDashboardTab('overview');
                }}
                style={{ cursor: 'pointer' }}
              >
                Dashboard
              </span>
              <span 
                className={`nav-link ${activeDashboardTab === 'coach' ? 'active' : ''}`}
                onClick={() => {
                  setShowLandingPage(false);
                  setActiveDashboardTab('coach');
                }}
                style={{ cursor: 'pointer' }}
              >
                AI Coach
              </span>
            </>
          )}
        </nav>

        <div className="auth-buttons">
          {!user ? (
            <>
              <button className="btn-flat-secondary" onClick={openLogin} style={{ padding: '0.5rem 1.2rem', fontSize: '0.85rem' }}>Log In</button>
              <button className="btn-flat-primary" onClick={openSignup} style={{ padding: '0.5rem 1.2rem', fontSize: '0.85rem' }}>Sign Up</button>
            </>
          ) : (
            <>
              <div className="live-clock" aria-live="polite">
                {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </div>
              <div className="profile-avatar-menu">
                <button className="profile-avatar-button" onClick={() => setActiveProfileView(activeProfileView === 'profile' ? 'dashboard' : 'profile')}>
                  <img src={activeProfileImage} alt="Profile" className="profile-avatar-image" />
                  <span className="profile-avatar-label">
                    {[user.firstName, user.middleName, user.lastName].filter(Boolean).join(' ') || user.username || user.email.split('@')[0]}
                  </span>
                </button>
              </div>
              <button className="btn-flat-secondary" onClick={handleLogout} style={{ padding: '0.5rem 1.2rem', fontSize: '0.85rem' }}>Log Out</button>
            </>
          )}
        </div>
      </header>

      {/* PAGE BODY */}
      {!user || showLandingPage ? (
        <>
          {/* SPA section switching based on activeSection */}

          {/* SECTION 1: HERO */}
          {activeSection === 'home' && (
          <>
            <div className="landing-container">
              {HERO_FOOD_IMAGES.map((img, idx) => (
                <div
                  key={idx}
                  className={`hero-food-image ${idx === heroImageIndex ? 'active' : ''}`}
                  style={{ backgroundImage: `url(${img})` }}
                  aria-hidden="true"
                />
              ))}
              <main className="content-overlay">
                <span className="title-badge">Personalized Health Platform</span>
                <h1 className="main-title">
                  Smart nutrition management,<br />tailored for you.
                </h1>
                <p className="main-description">
                  Calculate your BMI and BMR, discover personalized food recommendations, track your meals, and monitor your nutrition progress — all in one place.
                </p>
                <div className="cta-group">
                  <button className="btn-flat-primary" onClick={openSignup}>Get Started</button>
                  <button className="btn-flat-secondary" onClick={() => setActiveSection('search')}>
                    Search Foods
                  </button>
                </div>
              </main>
              <div style={{ height: '80px' }}></div>
            </div>
            <section className="nutrition-pulse-section" aria-labelledby="nutrition-pulse-title">
              <div className="pulse-copy">
                <span className="features-subtitle">A little inspiration</span>
                <h2 className="features-title" id="nutrition-pulse-title">Find something worth trying.</h2>
                <p className="search-description">Discover food ideas, culture, and practical nutrition notes. Nothing here is a prescription.</p>
                <div className="pulse-foods discovery-tabs" role="group" aria-label="Choose a discovery">
                  {DISCOVERY_ITEMS.map(item => (
                    <button
                      key={item.title}
                      type="button"
                      className={`pulse-food-button ${selectedDiscovery.title === item.title ? 'selected' : ''}`}
                      onClick={() => {
                        setSelectedDiscovery(item);
                        setSelectedInsightIndex(getDailyInsightIndex(item.insights.length));
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="pulse-panel discovery-panel">
                <div className="discovery-content" key={`${selectedDiscovery.title}-${selectedInsightIndex}`}>
                  <div className="pulse-panel-header">
                    <span>{selectedDiscovery.label}</span>
                    <strong>{selectedDiscovery.insights[selectedInsightIndex].statValue}</strong>
                  </div>
                  <h3>{selectedDiscovery.insights[selectedInsightIndex].headline}</h3>
                  <p className="discovery-description">{selectedDiscovery.insights[selectedInsightIndex].description}</p>
                  <div className="discovery-detail">
                    <span>{selectedDiscovery.insights[selectedInsightIndex].statLabel}</span>
                    <strong>{selectedDiscovery.insights[selectedInsightIndex].detail}</strong>
                  </div>
                </div>
              </div>
            </section>
          </>
          )}

          {/* SECTION 2: INTERACTIVE FOOD SEARCH */}
          {activeSection === 'search' && (
          <section className="search-section">
            <div className="search-header">
              <span className="features-subtitle">Nutrient Database</span>
              <h2 className="features-title">Analyze what you eat</h2>
              <p className="search-description">
                Search our extensive nutritional database to find calorie and macronutrient breakdowns for everyday foods.
              </p>
            </div>
            <form onSubmit={handleLandingSearch} className="search-bar-container">
              <input
                type="text"
                className="search-input"
                placeholder="Search food items (e.g. Oatmeal, Eggs, Chicken...)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button type="submit" className="btn-flat-primary search-btn">Search</button>
            </form>
            {searched && (
              <div className="results-container">
                {searchResults.length > 0 ? (
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Food Item</th>
                        <th>Category</th>
                        <th>Calories</th>
                        <th>Protein</th>
                        <th>Carbs</th>
                        <th>Fat</th>
                      </tr>
                    </thead>
                    <tbody>
                      {searchResults.map((food, idx) => (
                        <tr key={idx}>
                          <td className="food-name-cell">{food.name}</td>
                          <td><span className="category-badge">{food.category}</span></td>
                          <td className="calorie-cell">{food.calories} kcal</td>
                          <td>{food.protein}g</td>
                          <td>{food.carbs}g</td>
                          <td>{food.fat}g</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="no-results">
                    No food items found matching "{query}". Try searching for Oatmeal, Eggs, or Salmon!
                  </div>
                )}
              </div>
            )}
          </section>

          )}

          {/* SECTION 3: FEATURES CARDS SECTION */}
          {activeSection === 'features' && (
          <section className="features-section">
            <div className="features-header">
              <span className="features-subtitle">Features Overview</span>
              <h2 className="features-title">Everything you need to reach your goals</h2>
            </div>
            <div className="cards-grid">
              <div className="feature-card">
                <div className="card-icon">🎯</div>
                <h3 className="card-heading">Personalized Recommendations</h3>
                <p className="card-desc">
                  Get customized food and recipe suggestions generated specifically for your physical profile, calorie targets, and dietary preferences.
                </p>
              </div>
              <div className="feature-card">
                <div className="card-icon">📊</div>
                <h3 className="card-heading">Track & Monitor</h3>
                <p className="card-desc">
                  Log your daily meals easily, track nutrient breakdowns (protein, carbs, fats), and watch your long-term progress dynamically.
                </p>
              </div>
              <div className="feature-card">
                <div className="card-icon">💬</div>
                <h3 className="card-heading">AI Nutrition Coach</h3>
                <p className="card-desc">
                  Ask your conversational assistant nutrition queries and receive tailored advice based on your health goals and profile.
                </p>
              </div>
            </div>
          </section>
          )}
        </>
      ) : (
        /* LOGGED IN USER DASHBOARD */
        <div className="dashboard-container">
          {activeProfileView === 'profile' ? (
            <div className="profile-page">
              <div className="dashboard-card profile-header-card">
                <div className="profile-header-top">
                  <div className="profile-avatar-region">
                    <div className="profile-avatar-large-wrap">
                      <img src={activeProfileImage} alt="Profile" className="profile-avatar-large" />
                    </div>
                    <label className="upload-photo-button" title="Upload profile photo">
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden-upload-input"
                        onChange={handleAvatarUpload}
                      />
                      <span>Upload Photo</span>
                    </label>
                  </div>
                  <div>
                    <p className="profile-kicker">Your Profile</p>
                    <h2>{user?.email}</h2>
                  </div>
                </div>
                <div className="profile-mini-grid">
                  <div className="mini-stat">
                    <span>Age:</span>
                    <strong>{user?.profile?.age ?? 0}</strong>
                  </div>
                  <div className="mini-stat">
                    <span>Height:</span>
                    <strong>{user?.profile?.height ?? 0} cm</strong>
                  </div>
                  <div className="mini-stat">
                    <span>Weight:</span>
                    <strong>{user?.profile?.weight ?? 0} kg</strong>
                  </div>
                  <div className="mini-stat">
                    <span>Goal:</span>
                    <strong>{user?.profile?.fitnessGoal ?? 'Set a goal'}</strong>
                  </div>
                </div>
              </div>

              <div className="profile-grid">
                <div className="dashboard-card profile-detail-card">
                  <h3>Health Snapshot</h3>
                  <ul className="profile-detail-list">
                    <li><span>BMI:</span><strong>{user?.profile?.bmi ?? 0}</strong></li>
                    <li><span>BMR:</span><strong>{user?.profile?.bmr ?? 0} kcal</strong></li>
                    <li><span>Activity:</span><strong>{user?.profile?.activityLevel ?? 'Not set'}</strong></li>
                    <li><span>Diet:</span><strong>{user?.profile?.dietaryPreference ?? 'Not set'}</strong></li>
                    <li><span>Target Calories:</span><strong>{user?.profile?.targetCalories ?? 0} kcal</strong></li>
                    <li><span>Target Protein:</span><strong>{user?.profile?.targetProtein ?? 0} g</strong></li>
                  </ul>
                </div>

                <div className="dashboard-card usage-card">
                  <h3>Usage & Token Tracker</h3>
                  <div className="usage-meter-wrap">
                    <div className="usage-header-row">
                      <span>AI Coach Usage</span>
                      <strong>{usageEstimate.tokens} / 2000</strong>
                    </div>
                    <div className="usage-meter-bg">
                      <div className="usage-meter-fill" style={{ width: `${Math.min((usageEstimate.tokens / 2000) * 100, 100)}%` }}></div>
                    </div>
                  </div>
                  <div className="usage-note">
                    A lightweight estimate of AI usage based on nutrition coach prompts and meal tracking activity during the current session.
                  </div>
                  <div className="usage-summary-grid">
                    <div className="usage-tile">
                      <span>Coach Prompts</span>
                      <strong>{usageEstimate.prompts}</strong>
                    </div>
                    <div className="usage-tile">
                      <span>Estimated Tokens</span>
                      <strong>{usageEstimate.tokens}</strong>
                    </div>
                  </div>
                </div>
              </div>

              <div className="dashboard-card profile-action-card">
                <h3>Profile Actions</h3>
                <div className="profile-actions-row">
                  <button className="btn-flat-primary" onClick={() => setActiveProfileView('dashboard')}>Back to Dashboard</button>
                  <button className="btn-flat-secondary" onClick={() => setActiveDashboardTab('coach')}>Open AI Coach</button>
                </div>
              </div>
            </div>
          ) : activeDashboardTab === 'overview' ? (
            <div className="dashboard-grid">
              <div className="dashboard-left">
                <div className="dashboard-card profile-metrics-card">
                  <h3>Your Health Profile</h3>
                  <div className="profile-stats">
                    <div className="stat-box">
                      <span className="stat-lbl">BMI</span>
                      <span className="stat-val">{user.profile?.bmi}</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-lbl">BMR</span>
                      <span className="stat-val">{user.profile?.bmr} kcal</span>
                    </div>
                    <div className="stat-box">
                      <span className="stat-lbl">Daily Budget</span>
                      <span className="stat-val">{user.profile?.targetCalories} kcal</span>
                    </div>
                  </div>
                  <div className="profile-details-list">
                    <p><strong>Goal:</strong> {user.profile?.fitnessGoal}</p>
                    <p><strong>Preference:</strong> {user.profile?.dietaryPreference}</p>
                    <p><strong>Activity Level:</strong> {user.profile?.activityLevel}</p>
                  </div>
                </div>

                <div className="dashboard-card progress-card">
                  <h3>Today's Consumption Progress</h3>
                  <div className="metric-progress-wrapper">
                    <div className="metric-header">
                      <span>Calories</span>
                      <span>{totalCals} / {user.profile?.targetCalories} kcal</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div 
                        className="progress-bar-fill cal-fill" 
                        style={{ width: `${Math.min((totalCals / (user.profile?.targetCalories || 1)) * 100, 100)}%` }}
                      ></div>
                    </div>
                  </div>

                  <div className="macros-progress-grid">
                    <div className="macro-progress-box">
                      <div className="macro-lbl">Protein</div>
                      <div className="macro-bar-bg">
                        <div 
                          className="macro-bar-fill prot-fill" 
                          style={{ height: `${Math.min((totalProtein / (user.profile?.targetProtein || 1)) * 100, 100)}%` }}
                        ></div>
                      </div>
                      <span className="macro-text">{totalProtein}g / {user.profile?.targetProtein}g</span>
                    </div>

                    <div className="macro-progress-box">
                      <div className="macro-lbl">Carbs</div>
                      <div className="macro-bar-bg">
                        <div 
                          className="macro-bar-fill carb-fill" 
                          style={{ height: `${Math.min((totalCarbs / (user.profile?.targetCarbs || 1)) * 100, 100)}%` }}
                        ></div>
                      </div>
                      <span className="macro-text">{totalCarbs}g / {user.profile?.targetCarbs}g</span>
                    </div>

                    <div className="macro-progress-box">
                      <div className="macro-lbl">Fat</div>
                      <div className="macro-bar-bg">
                        <div 
                          className="macro-bar-fill fat-fill" 
                          style={{ height: `${Math.min((totalFat / (user.profile?.targetFat || 1)) * 100, 100)}%` }}
                        ></div>
                      </div>
                      <span className="macro-text">{totalFat}g / {user.profile?.targetFat}g</span>
                    </div>
                  </div>
                </div>

                <div className="dashboard-card log-meal-card">
                  <h3>Track a Meal</h3>
                  <form onSubmit={handleLogMealSubmit}>
                    <div className="form-field-container">
                      <label>Search Food</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="Type to search (e.g. Eggs, Oatmeal...)"
                        value={logFoodQuery}
                        onChange={(e) => handleLogFoodSearch(e.target.value)}
                      />
                      {logFoodResults.length > 0 && (
                        <div className="search-dropdown">
                          {logFoodResults.map((food, idx) => (
                            <div 
                              key={idx} 
                              className="dropdown-item" 
                              onClick={() => handleSelectFoodToLog(food)}
                            >
                              <span>{food.name}</span>
                              <span style={{ fontSize: '0.8rem', opacity: 0.7 }}>({food.calories} kcal)</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {selectedFood && (
                      <div className="selected-food-details">
                        Selected: <strong>{selectedFood.name}</strong> ({selectedFood.calories} kcal per serving)
                      </div>
                    )}

                    <div className="log-row">
                      <div className="form-field-container">
                        <label>Servings / Quantity</label>
                        <input
                          type="number"
                          min="0.25"
                          step="0.25"
                          className="form-input"
                          value={mealQty}
                          onChange={(e) => setMealQty(parseFloat(e.target.value) || 1)}
                        />
                      </div>
                      <div className="form-field-container">
                        <label>Meal Type</label>
                        <select 
                          className="form-input" 
                          value={mealType} 
                          onChange={(e) => setMealType(e.target.value)}
                        >
                          <option>Breakfast</option>
                          <option>Lunch</option>
                          <option>Dinner</option>
                          <option>Snack</option>
                        </select>
                      </div>
                    </div>

                    <button 
                      type="submit" 
                      className="btn-flat-primary" 
                      style={{ width: '100%', marginTop: '1rem' }} 
                      disabled={!selectedFood}
                    >
                      Log Meal
                    </button>
                  </form>
                </div>
              </div>

              <div className="dashboard-right">
                <div className="dashboard-card meal-history-card" style={{ height: '100%' }}>
                  <h3>Today's Meal Log</h3>
                  {trackedMeals.length > 0 ? (
                    <div className="logged-meals-list">
                      {trackedMeals.map((meal, idx) => (
                        <div key={idx} className="logged-meal-item">
                          <div className="meal-details">
                            <span className="meal-title-name">{meal.name}</span>
                            <span className="meal-meta">{meal.mealType} • {meal.quantity} serving(s)</span>
                          </div>
                          <div className="meal-macros-summary">
                            <span>{meal.calories} kcal</span>
                            <button className="btn-remove-meal" onClick={() => handleRemoveLoggedMeal(idx)}>×</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="empty-logs-text">No meals logged today yet. Use the form to start tracking!</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="coach-tab-container" style={{ maxWidth: '800px', margin: '0 auto' }}>
              <div className="dashboard-card chatbot-card" style={{ height: '600px' }}>
                <h3>AI Nutrition Assistant</h3>
                <div className="chatbot-chatbox">
                  {chatMessages.map((msg, idx) => (
                    <div key={idx} className={`chat-bubble ${msg.sender === 'user' ? 'user-bubble' : 'coach-bubble'}`}>
                      {msg.text}
                    </div>
                  ))}
                </div>
                <form onSubmit={handleSendMessage} className="chatbot-input-form">
                  <input
                    type="text"
                    className="chat-input"
                    placeholder="Ask about your targets, meals, protein..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                  />
                  <button type="submit" className="btn-flat-primary chat-send-btn">Send</button>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* FOOTER - always visible */}
      <footer className="root-footer">
        <div className="footer-content" style={{ justifyContent: 'center' }}>
          <span>© 2026 NutritionAI</span>
        </div>
      </footer>

      {/* MODAL WRAPPER */}
      {activeModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <button className="modal-close" onClick={() => setActiveModal(null)}>×</button>
            
            {activeModal === 'login' && (
              <form onSubmit={handleLogin} className="auth-form">
                <h2>Welcome Back</h2>
                <p>Log in to access your personal nutrition dashboard.</p>
                <div className="form-field-container">
                  <label>Email Address</label>
                  <input 
                    type="email" 
                    required 
                    className="form-input" 
                    placeholder="name@example.com" 
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                  />
                </div>
                <div className="form-field-container">
                  <label>Password</label>
                  <input 
                    type="password" 
                    required 
                    className="form-input" 
                    placeholder="••••••••" 
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                  />
                </div>
                <button type="submit" className="btn-flat-primary" style={{ width: '100%', marginTop: '1rem' }}>Log In</button>
                <p className="auth-toggle-link">
                  Don't have an account? <span onClick={openSignup}>Sign Up</span>
                </p>
              </form>
            )}

            {activeModal === 'signup' && (
              <form onSubmit={handleSignupSubmit} className="auth-form">
                <h2>Create Account</h2>
                <p>Build your profile and get personalized nutrition calculations.</p>
                <div className="form-field-container">
                  <label>First Name</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="First name"
                    value={authFirstName}
                    onChange={(e) => setAuthFirstName(e.target.value)}
                  />
                </div>
                <div className="form-field-container">
                  <label>Middle Name (optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Middle name"
                    value={authMiddleName}
                    onChange={(e) => setAuthMiddleName(e.target.value)}
                  />
                </div>
                <div className="form-field-container">
                  <label>Last Name</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="Last name"
                    value={authLastName}
                    onChange={(e) => setAuthLastName(e.target.value)}
                  />
                </div>
                <div className="form-field-container">
                  <label>Email Address</label>
                  <input 
                    type="email" 
                    required 
                    className="form-input" 
                    placeholder="name@example.com" 
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                  />
                </div>
                <div className="form-field-container">
                  <label>Password</label>
                  <input 
                    type="password" 
                    required 
                    className="form-input" 
                    placeholder="••••••••" 
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                  />
                </div>
                <button type="submit" className="btn-flat-primary" style={{ width: '100%', marginTop: '1rem' }}>Continue to Profile Setup</button>
                <p className="auth-toggle-link">
                  Already have an account? <span onClick={openLogin}>Log In</span>
                </p>
              </form>
            )}

            {activeModal === 'profile' && (
              <form onSubmit={handleProfileSubmit} className="auth-form profile-setup-form">
                <h2>Health Profile</h2>
                <p>Provide your details to calculate your BMI, BMR, and daily macro budgets.</p>
                
                <div className="profile-form-grid">
                  <div className="form-field-container">
                    <label>Age (years)</label>
                    <input 
                      type="number" 
                      required 
                      className="form-input" 
                      min="10" 
                      max="100"
                      value={age}
                      onChange={(e) => setAge(parseInt(e.target.value) || 25)}
                    />
                  </div>

                  <div className="form-field-container">
                    <label>Gender</label>
                    <select 
                      className="form-input" 
                      value={gender} 
                      onChange={(e) => setGender(e.target.value as 'Male' | 'Female')}
                    >
                      <option>Male</option>
                      <option>Female</option>
                    </select>
                  </div>

                  <div className="form-field-container">
                    <label>Height (cm)</label>
                    <input 
                      type="number" 
                      required 
                      className="form-input" 
                      min="100" 
                      max="250"
                      value={height}
                      onChange={(e) => setHeight(parseInt(e.target.value) || 175)}
                    />
                  </div>

                  <div className="form-field-container">
                    <label>Weight (kg)</label>
                    <input 
                      type="number" 
                      required 
                      className="form-input" 
                      min="30" 
                      max="200"
                      value={weight}
                      onChange={(e) => setWeight(parseInt(e.target.value) || 70)}
                    />
                  </div>

                  <div className="form-field-container">
                    <label>Activity Level</label>
                    <select 
                      className="form-input"
                      value={activity}
                      onChange={(e) => setActivity(e.target.value as HealthProfile['activityLevel'])}
                    >
                      <option>Sedentary</option>
                      <option>Lightly Active</option>
                      <option>Moderately Active</option>
                      <option>Very Active</option>
                    </select>
                  </div>

                  <div className="form-field-container">
                    <label>Fitness Goal</label>
                    <select 
                      className="form-input"
                      value={goal}
                      onChange={(e) => setGoal(e.target.value as HealthProfile['fitnessGoal'])}
                    >
                      <option>Lose Weight</option>
                      <option>Maintain Weight</option>
                      <option>Gain Weight</option>
                    </select>
                  </div>

                  <div className="form-field-container">
                    <label>Dietary Preference</label>
                    <select 
                      className="form-input"
                      value={diet}
                      onChange={(e) => setDiet(e.target.value as HealthProfile['dietaryPreference'])}
                    >
                      <option>None</option>
                      <option>Vegetarian</option>
                      <option>Vegan</option>
                      <option>Keto</option>
                    </select>
                  </div>
                </div>

                <button type="submit" className="btn-flat-primary" style={{ width: '100%', marginTop: '1.5rem' }}>
                  Generate Dashboard & Targets
                </button>
              </form>
            )}
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
