import { useEffect, useState } from 'react';

import type { ApiFood } from '../api/types';
import { DISCOVERY_ITEMS, HERO_FOOD_IMAGES, dailyInsightIndex } from '../lib/content';
import type { DiscoveryItem } from '../lib/content';
import type { LandingSection } from './Navbar';

interface LandingProps {
  section: LandingSection;
  onGetStarted: () => void;
  onSelectSection: (section: LandingSection) => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  onSearch: (event: React.FormEvent) => void;
  searchResults: ApiFood[];
  searched: boolean;
  searching: boolean;
  searchError?: string | null;
}


function dietBadge(food: ApiFood): string {
  if (food.is_vegan) return '🌿 Vegan (Veg)';
  if (food.is_vegetarian) return '🥛 Vegetarian';
  return '🥩 Non-Veg';
}

function Hero({ onGetStarted, onSelectSection }: Pick<LandingProps, 'onGetStarted' | 'onSelectSection'>) {
  const [heroIndex, setHeroIndex] = useState(0);
  const [discovery, setDiscovery] = useState<DiscoveryItem>(DISCOVERY_ITEMS[0]);
  const [insightIndex, setInsightIndex] = useState(() => dailyInsightIndex(DISCOVERY_ITEMS[0].insights.length));

  useEffect(() => {
    const timer = window.setInterval(
      () => setHeroIndex((index) => (index + 1) % HERO_FOOD_IMAGES.length),
      5000,
    );
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(
      () => setInsightIndex((index) => (index + 1) % discovery.insights.length),
      5000,
    );
    return () => window.clearInterval(timer);
  }, [discovery]);

  const insight = discovery.insights[insightIndex];

  return (
    <>
      <div className="landing-container">
        {HERO_FOOD_IMAGES.map((image, index) => (
          <div
            key={image}
            className={`hero-food-image ${index === heroIndex ? 'active' : ''}`}
            style={{ backgroundImage: `url(${image})` }}
            aria-hidden="true"
          />
        ))}
        <main className="content-overlay">
          <span className="title-badge">Personalized Health Platform</span>
          <h1 className="main-title">
            Smart nutrition management,<br />tailored for you.
          </h1>
          <p className="main-description">
            Calculate your BMI and BMR, discover personalized food recommendations, track your
            meals, and monitor your nutrition progress — all in one place.
          </p>
          <div className="cta-group">
            <button className="btn-flat-primary" onClick={onGetStarted}>Get Started</button>
            <button className="btn-flat-secondary" onClick={() => onSelectSection('search')}>
              Search Foods
            </button>
          </div>
        </main>
        <div style={{ height: '80px' }} />
      </div>

      <section className="nutrition-pulse-section" aria-labelledby="nutrition-pulse-title">
        <div className="pulse-copy">
          <span className="features-subtitle">A little inspiration</span>
          <h2 className="features-title" id="nutrition-pulse-title">Find something worth trying.</h2>
          <p className="search-description">
            Discover food ideas, culture, and practical nutrition notes. Nothing here is a prescription.
          </p>
          <div className="pulse-foods discovery-tabs" role="group" aria-label="Choose a discovery">
            {DISCOVERY_ITEMS.map((item) => (
              <button
                key={item.title}
                type="button"
                className={`pulse-food-button ${discovery.title === item.title ? 'selected' : ''}`}
                onClick={() => {
                  setDiscovery(item);
                  setInsightIndex(dailyInsightIndex(item.insights.length));
                }}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="pulse-panel discovery-panel">
          <div className="discovery-content" key={`${discovery.title}-${insightIndex}`}>
            <div className="pulse-panel-header">
              <span>{discovery.label}</span>
              <strong>{insight.statValue}</strong>
            </div>
            <h3>{insight.headline}</h3>
            <p className="discovery-description">{insight.description}</p>
            <div className="discovery-detail">
              <span>{insight.statLabel}</span>
              <strong>{insight.detail}</strong>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

const CUISINE_OPTIONS = ['All', 'South Asian', 'East Asian', 'Western', 'Global'] as const;
const DIET_OPTIONS = ['All', 'Vegan', 'Vegetarian', 'Non-Vegetarian'] as const;

function FoodSearch({
  searchQuery,
  onSearchQueryChange,
  onSearch,
  searchResults,
  searched,
  searching,
  searchError,
}: Pick<LandingProps, 'searchQuery' | 'onSearchQueryChange' | 'onSearch' | 'searchResults' | 'searched' | 'searching' | 'searchError'>) {
  const [selectedCuisine, setSelectedCuisine] = useState<string>('All');
  const [selectedDiet, setSelectedDiet] = useState<string>('All');

  const filteredResults = searchResults.filter((food) => {
    const matchesCuisine =
      selectedCuisine === 'All' || food.region.toLowerCase() === selectedCuisine.toLowerCase();

    let matchesDiet = true;
    if (selectedDiet === 'Vegan') {
      matchesDiet = food.is_vegan;
    } else if (selectedDiet === 'Vegetarian') {
      // Anything vegan is also vegetarian by definition (no meat/poultry/fish).
      matchesDiet = food.is_vegetarian;
    } else if (selectedDiet === 'Non-Vegetarian') {
      matchesDiet = !food.is_vegetarian;
    }

    return matchesCuisine && matchesDiet;
  });

  const handleFormSubmit = (event: React.FormEvent) => {
    setSelectedCuisine('All');
    setSelectedDiet('All');
    onSearch(event);
  };

  return (
    <section className="search-section">
      <div className="search-header">
        <span className="features-subtitle">Nutrient Database</span>
        <h2 className="features-title">Analyze what you eat</h2>
        <p className="search-description">
          Search our nutritional database to find calorie and macronutrient breakdowns for
          everyday foods.
        </p>
      </div>

      <form onSubmit={handleFormSubmit} className="search-bar-container">
        <input
          type="text"
          className="search-input"
          placeholder="Search food items (e.g. Oatmeal, Chowmein, Momos, Dal Bhat...)"
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
          aria-label="Search food items"
        />
        <button type="submit" className="btn-flat-primary search-btn" disabled={searching}>
          {searching ? 'Searching…' : 'Search'}
        </button>
      </form>

      {searchError && (
        <div className="search-error-banner" role="alert">
          <span>⚠️</span>
          <span>{searchError}</span>
        </div>
      )}

      {searched && (
        <div className="results-container">
          {/* Filter chips bar */}
          <div className="search-filters-bar">
            <div className="search-filter-group">
              <span className="search-filter-label">Cuisine:</span>
              <div className="search-filter-chips">
                {CUISINE_OPTIONS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    className={`search-filter-chip ${selectedCuisine === c ? 'active' : ''}`}
                    onClick={() => setSelectedCuisine(c)}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>

            <div className="search-filter-group">
              <span className="search-filter-label">Diet:</span>
              <div className="search-filter-chips">
                {DIET_OPTIONS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`search-filter-chip ${selectedDiet === d ? 'active' : ''}`}
                    onClick={() => setSelectedDiet(d)}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {filteredResults.length > 0 ? (
            <table className="results-table">
              <thead>
                <tr>
                  <th>Food Item</th>
                  <th>Cuisine</th>
                  <th>Serving Size</th>
                  <th>Category</th>
                  <th>Calories</th>
                  <th>Protein</th>
                  <th>Carbs</th>
                  <th>Fat</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((food) => (
                  <tr key={food.id}>
                    <td className="food-name-cell">{food.name}</td>
                    <td>
                      <span className="cuisine-badge">{food.region}</span>
                    </td>
                    <td>
                      <span className="serving-size-cell">{food.serving_size}</span>
                    </td>
                    <td>
                      <span
                        className={`category-badge category-${
                          food.is_vegan
                            ? 'vegan'
                            : food.is_vegetarian
                            ? 'vegetarian'
                            : 'non-veg'
                        }`}
                        title={
                          food.is_vegan
                            ? 'Vegan: 100% plant-based, suitable for vegetarians'
                            : food.is_vegetarian
                            ? 'Vegetarian: Contains dairy/honey, no meat or seafood'
                            : 'Non-Vegetarian: Contains meat, poultry, or seafood'
                        }
                      >
                        {dietBadge(food)}
                      </span>
                    </td>
                    <td className="calorie-cell">{food.calories} kcal</td>
                    <td>{food.protein}g</td>
                    <td>{food.carbohydrates}g</td>
                    <td>{food.fat}g</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : searchResults.length > 0 ? (
            <div className="no-results">
              No items match the &quot;{selectedCuisine}&quot; cuisine and &quot;{selectedDiet}&quot; diet filter.
              <button
                type="button"
                className="btn-filter-reset"
                onClick={() => {
                  setSelectedCuisine('All');
                  setSelectedDiet('All');
                }}
              >
                Clear filters to show all {searchResults.length} results
              </button>
            </div>
          ) : (
            <div className="no-results">
              No food items found matching &quot;{searchQuery}&quot;. Try Oatmeal, Chowmein, Momos, or Dal Bhat.
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Features() {
  const cards = [
    {
      icon: '🎯',
      heading: 'Personalized Recommendations',
      description:
        'Food suggestions generated for your physical profile, calorie targets and dietary preferences.',
    },
    {
      icon: '📊',
      heading: 'Track & Monitor',
      description:
        'Log daily meals, see your protein, carbohydrate and fat breakdown, and watch progress against your targets.',
    },
    {
      icon: '💬',
      heading: 'AI Nutrition Coach',
      description:
        'Ask nutrition questions and get answers that draw on your own profile and what you have eaten today.',
    },
  ];

  return (
    <section className="features-section">
      <div className="features-header">
        <span className="features-subtitle">Features Overview</span>
        <h2 className="features-title">Everything you need to reach your goals</h2>
      </div>
      <div className="cards-grid">
        {cards.map((card) => (
          <div className="feature-card" key={card.heading}>
            <div className="card-icon" aria-hidden="true">{card.icon}</div>
            <h3 className="card-heading">{card.heading}</h3>
            <p className="card-desc">{card.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Landing(props: LandingProps) {
  const { section } = props;
  if (section === 'home') {
    return <Hero onGetStarted={props.onGetStarted} onSelectSection={props.onSelectSection} />;
  }
  if (section === 'search') return <FoodSearch {...props} />;
  return <Features />;
}
