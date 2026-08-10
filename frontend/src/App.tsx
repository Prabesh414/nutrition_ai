import { useState } from 'react';
import './App.css';

const MOCK_FOODS = [
  { name: 'Oatmeal', calories: 150, protein: 5, carbs: 27, fat: 3, category: 'Breakfast' },
  { name: 'Eggs (2 large)', calories: 140, protein: 12, carbs: 1, fat: 10, category: 'Breakfast' },
  { name: 'Chicken Breast (100g)', calories: 165, protein: 31, carbs: 0, fat: 3.6, category: 'Lunch' },
  { name: 'Salmon (100g)', calories: 206, protein: 22, carbs: 0, fat: 13, category: 'Dinner' },
  { name: 'Greek Yogurt (150g)', calories: 120, protein: 15, carbs: 6, fat: 4, category: 'Snacks' },
  { name: 'Apple', calories: 95, protein: 0.5, carbs: 25, fat: 0.3, category: 'Snacks' },
  { name: 'Brown Rice (1 cup)', calories: 215, protein: 5, carbs: 45, fat: 1.6, category: 'Lunch' },
  { name: 'Almonds (28g)', calories: 164, protein: 6, carbs: 6, fat: 14, category: 'Snacks' }
];

interface HealthProfile {
  age: number;
  gender: 'Male' | 'Female';
  height: number;
  weight: number;
  activityLevel: 'Sedentary' | 'Lightly Active' | 'Moderately Active' | 'Very Active';
  fitnessGoal: 'Lose Weight' | 'Maintain Weight' | 'Gain Weight';
  dietaryPreference: 'None' | 'Vegetarian' | 'Vegan' | 'Keto';
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

function App() {
  // Navigation & Page Tab State
  const [activeSection, setActiveSection] = useState<'home' | 'search' | 'features'>('home');
  const [activeDashboardTab, setActiveDashboardTab] = useState<'overview' | 'coach'>('overview');

  // Search State
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<typeof MOCK_FOODS>([]);
  const [searched, setSearched] = useState(false);

  // Authentication State
  const [user, setUser] = useState<{ email: string; profile: HealthProfile | null } | null>(null);
  const [activeModal, setActiveModal] = useState<'login' | 'signup' | 'profile' | null>(null);

  // Form Fields
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
    const filtered = MOCK_FOODS.filter(food =>
      food.name.toLowerCase().includes(query.toLowerCase())
    );
    setSearchResults(filtered);
    setSearched(true);
  };

  // Auth actions
  const openLogin = () => {
    setAuthEmail('');
    setAuthPassword('');
    setActiveModal('login');
  };

  const openSignup = () => {
    setAuthEmail('');
    setAuthPassword('');
    setActiveModal('signup');
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (authEmail && authPassword) {
      setUser({
        email: authEmail,
        profile: {
          age: 25,
          gender: 'Male',
          height: 175,
          weight: 70,
          activityLevel: 'Moderately Active',
          fitnessGoal: 'Maintain Weight',
          dietaryPreference: 'None',
          bmi: 22.9,
          bmr: 1680,
          targetCalories: 2100,
          targetProtein: 131,
          targetCarbs: 236,
          targetFat: 70
        }
      });
      setActiveModal(null);
      setActiveDashboardTab('overview');
    }
  };

  const handleSignupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (authEmail && authPassword) {
      setActiveModal('profile');
    }
  };

  const handleProfileSubmit = (e: React.FormEvent) => {
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

    setUser({
      email: authEmail,
      profile: {
        age,
        gender,
        height,
        weight,
        activityLevel: activity,
        fitnessGoal: goal,
        dietaryPreference: diet,
        bmi,
        bmr,
        targetCalories,
        targetProtein,
        targetCarbs,
        targetFat
      }
    });

    setActiveModal(null);
    setActiveDashboardTab('overview');
  };

  const handleLogout = () => {
    setUser(null);
    setTrackedMeals([]);
    setSelectedFood(null);
    setLogFoodQuery('');
    setLogFoodResults([]);
    setActiveSection('home');
  };

  // Log meals logic
  const handleLogFoodSearch = (val: string) => {
    setLogFoodQuery(val);
    if (!val.trim()) {
      setLogFoodResults([]);
      return;
    }
    const filtered = MOCK_FOODS.filter(food =>
      food.name.toLowerCase().includes(val.toLowerCase())
    );
    setLogFoodResults(filtered);
  };

  const handleSelectFoodToLog = (food: typeof MOCK_FOODS[0]) => {
    setSelectedFood(food);
    setLogFoodQuery(food.name);
    setLogFoodResults([]);
  };

  const handleLogMealSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFood) return;

    const newLog: LoggedMeal = {
      name: selectedFood.name,
      quantity: mealQty,
      mealType,
      calories: Math.round(selectedFood.calories * mealQty),
      protein: Math.round(selectedFood.protein * mealQty),
      carbs: Math.round(selectedFood.carbs * mealQty),
      fat: Math.round(selectedFood.fat * mealQty)
    };

    setTrackedMeals([...trackedMeals, newLog]);
    setSelectedFood(null);
    setLogFoodQuery('');
    setMealQty(1);
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
        <div className="brand" onClick={handleLogout} style={{ cursor: 'pointer' }}>
          Nutrition<span className="brand-dot">AI</span>
        </div>
        
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
                onClick={() => setActiveDashboardTab('overview')}
                style={{ cursor: 'pointer' }}
              >
                Dashboard
              </span>
              <span 
                className={`nav-link ${activeDashboardTab === 'coach' ? 'active' : ''}`}
                onClick={() => setActiveDashboardTab('coach')}
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
              <span className="user-email">{user.email}</span>
              <button className="btn-flat-secondary" onClick={handleLogout} style={{ padding: '0.5rem 1.2rem', fontSize: '0.85rem' }}>Log Out</button>
            </>
          )}
        </div>
      </header>

      {/* PAGE BODY */}
      {!user ? (
        <>
          {/* SPA section switching based on activeSection */}

          {/* SECTION 1: HERO */}
          {activeSection === 'home' && (
          <div className="landing-container">
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
          {activeDashboardTab === 'overview' ? (
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
