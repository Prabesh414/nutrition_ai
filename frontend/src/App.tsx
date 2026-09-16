/**
 * Application shell.
 *
 * Composition only: data access lives in `api/`, stateful behaviour in
 * `hooks/`, and rendering in `components/`. This file was previously a single
 * 2,343-line component holding 46 pieces of state.
 */
import { useCallback, useEffect, useState } from 'react';

import './App.css';
import maleAvatar from './assets/png/male.png';
import womanAvatar from './assets/png/woman.png';
import { api } from './api/client';
import type { ApiFood, MealType, ProfileInput } from './api/types';
import { AuthModals } from './components/AuthModals';
import type { ModalKind, SignupDraft } from './components/AuthModals';
import { CoachPanel, FloatingCoach } from './components/Coach';
import { Dashboard } from './components/Dashboard';
import { Landing } from './components/Landing';
import { Navbar } from './components/Navbar';
import type { DashboardTab, LandingSection, ProfileView } from './components/Navbar';
import { ProfilePage } from './components/ProfilePage';
import { useCoach } from './hooks/useCoach';
import { useDailyLog } from './hooks/useDailyLog';
import { useSession } from './hooks/useSession';

function App() {
  const session = useSession();
  const { user } = session;

  const dailyLog = useDailyLog(Boolean(user));
  const coach = useCoach();

  const [showLanding, setShowLanding] = useState(false);
  const [activeSection, setActiveSection] = useState<LandingSection>('home');
  const [activeDashboardTab, setActiveDashboardTab] = useState<DashboardTab>('overview');
  const [activeProfileView, setActiveProfileView] = useState<ProfileView>('dashboard');
  const [modal, setModal] = useState<ModalKind>(null);
  const [currentTime, setCurrentTime] = useState(() => new Date());

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ApiFood[]>([]);
  const [searched, setSearched] = useState(false);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const avatarUrl =
    user?.profile?.profile_image_url ||
    (user?.profile?.gender === 'Female' ? womanAvatar : maleAvatar);

  const handleSearch = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!searchQuery.trim()) {
        setSearchResults([]);
        setSearched(false);
        return;
      }
      setSearching(true);
      try {
        setSearchResults(await api.searchFoods(searchQuery));
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
        setSearched(true);
      }
    },
    [searchQuery],
  );

  const handleLogin = useCallback(
    async (email: string, password: string) => {
      await session.login(email, password);
      setModal(null);
      setShowLanding(false);
      setActiveDashboardTab('overview');
      setActiveProfileView('dashboard');
    },
    [session],
  );

  const handleRegister = useCallback(
    async (draft: SignupDraft) => {
      await session.register({
        first_name: draft.first_name,
        middle_name: draft.middle_name || null,
        last_name: draft.last_name,
        email: draft.email,
        password: draft.password,
      });
      // The account exists; collect the health details next.
      setModal('profile');
    },
    [session],
  );

  const handleSaveProfile = useCallback(
    async (input: ProfileInput) => {
      await session.saveProfile(input);
      await dailyLog.refresh();
      setShowLanding(false);
    },
    [session, dailyLog],
  );

  const handleLogMeal = useCallback(
    async (food: ApiFood, quantity: number, mealType: MealType) => {
      await dailyLog.addMeal({
        name: food.name,
        quantity,
        meal_type: mealType,
        calories: Math.round(food.calories * quantity),
        protein: Math.round(food.protein * quantity * 10) / 10,
        carbs: Math.round(food.carbohydrates * quantity * 10) / 10,
        fat: Math.round(food.fat * quantity * 10) / 10,
        fiber: Math.round(food.fiber * quantity * 10) / 10,
      });
    },
    [dailyLog],
  );

  const handleLogout = useCallback(() => {
    session.logout();
    setShowLanding(false);
    setActiveSection('home');
    setActiveProfileView('dashboard');
    setActiveDashboardTab('overview');
  }, [session]);

  if (session.loading) {
    return (
      <div className="landing-wrapper">
        <div className="session-loading">Loading your dashboard…</div>
      </div>
    );
  }

  const showLandingPages = !user || showLanding;

  return (
    <div className="landing-wrapper">
      <Navbar
        user={user}
        showLanding={showLanding}
        activeSection={activeSection}
        activeDashboardTab={activeDashboardTab}
        activeProfileView={activeProfileView}
        currentTime={currentTime}
        avatarUrl={avatarUrl}
        onBrandClick={() => {
          if (user) {
            setShowLanding(false);
            setActiveProfileView('dashboard');
            setActiveDashboardTab('overview');
          } else {
            setActiveSection('home');
          }
        }}
        onSelectSection={(section) => {
          setShowLanding(true);
          setActiveSection(section);
        }}
        onSelectDashboardTab={(tab) => {
          setShowLanding(false);
          setActiveDashboardTab(tab);
          setActiveProfileView('dashboard');
        }}
        onToggleProfileView={() =>
          setActiveProfileView((view) => (view === 'profile' ? 'dashboard' : 'profile'))
        }
        onLogin={() => setModal('login')}
        onSignup={() => setModal('signup')}
        onLogout={handleLogout}
      />

      {showLandingPages ? (
        <Landing
          section={activeSection}
          onGetStarted={() => setModal('signup')}
          onSelectSection={setActiveSection}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onSearch={handleSearch}
          searchResults={searchResults}
          searched={searched}
          searching={searching}
        />
      ) : (
        <div className="dashboard-container">
          {activeProfileView === 'profile' ? (
            <ProfilePage
              user={user}
              profile={user.profile}
              avatarUrl={avatarUrl}
              onSaveProfile={handleSaveProfile}
              onBackToDashboard={() => setActiveProfileView('dashboard')}
              onOpenCoach={() => {
                setActiveProfileView('dashboard');
                setActiveDashboardTab('coach');
              }}
            />
          ) : activeDashboardTab === 'overview' ? (
            <Dashboard
              profile={user.profile}
              summary={dailyLog.summary}
              recommendations={dailyLog.recommendations}
              loadingRecommendations={dailyLog.loadingRecommendations}
              error={dailyLog.error}
              onLogMeal={handleLogMeal}
              onRemoveMeal={dailyLog.removeMeal}
            />
          ) : (
            <CoachPanel coach={coach} />
          )}
        </div>
      )}

      <footer className="root-footer">
        <div className="footer-content footer-centered">
          <span>© 2026 NutritionAI</span>
          <span className="footer-disclaimer">
            Educational tool — not a substitute for professional medical or dietary advice.
          </span>
        </div>
      </footer>

      <AuthModals
        modal={modal}
        onClose={() => setModal(null)}
        onSwitch={setModal}
        onLogin={handleLogin}
        onRegister={handleRegister}
        onSaveProfile={handleSaveProfile}
      />

      {user && <FloatingCoach coach={coach} />}
    </div>
  );
}

export default App;
