import type { ApiUser } from '../api/types';
import { displayName } from '../hooks/useSession';

export type LandingSection = 'home' | 'search' | 'features';
export type DashboardTab = 'overview' | 'coach';
export type ProfileView = 'dashboard' | 'profile';

interface NavbarProps {
  user: ApiUser | null;
  showLanding: boolean;
  activeSection: LandingSection;
  activeDashboardTab: DashboardTab;
  activeProfileView: ProfileView;
  currentTime: Date;
  avatarUrl: string;
  onBrandClick: () => void;
  onSelectSection: (section: LandingSection) => void;
  onSelectDashboardTab: (tab: DashboardTab) => void;
  onToggleProfileView: () => void;
  onLogin: () => void;
  onSignup: () => void;
  onLogout: () => void;
}

const LANDING_LINKS: { section: LandingSection; label: string }[] = [
  { section: 'home', label: 'Home' },
  { section: 'search', label: 'Search Food' },
  { section: 'features', label: 'Features' },
];

export function Navbar({
  user,
  showLanding,
  activeSection,
  activeDashboardTab,
  activeProfileView,
  currentTime,
  avatarUrl,
  onBrandClick,
  onSelectSection,
  onSelectDashboardTab,
  onToggleProfileView,
  onLogin,
  onSignup,
  onLogout,
}: NavbarProps) {
  const landingActive = showLanding || !user;

  return (
    <header className="navbar">
      <button className="brand" type="button" onClick={onBrandClick} aria-label="Go to NutritionAI home">
        Nutrition<span className="brand-dot">AI</span>
      </button>

      <nav className="nav-links">
        {LANDING_LINKS.map(({ section, label }) => (
          <button
            key={section}
            type="button"
            className={`nav-link ${landingActive && activeSection === section ? 'active' : ''}`}
            onClick={() => onSelectSection(section)}
          >
            {label}
          </button>
        ))}

        {user && (
          <>
            <button
              type="button"
              className={`nav-link ${!showLanding && activeDashboardTab === 'overview' ? 'active' : ''}`}
              onClick={() => onSelectDashboardTab('overview')}
            >
              Dashboard
            </button>
            <button
              type="button"
              className={`nav-link ${!showLanding && activeDashboardTab === 'coach' ? 'active' : ''}`}
              onClick={() => onSelectDashboardTab('coach')}
            >
              AI Coach
            </button>
          </>
        )}
      </nav>

      <div className="auth-buttons">
        {!user ? (
          <>
            <button className="btn-flat-secondary nav-auth-btn" onClick={onLogin}>Log In</button>
            <button className="btn-flat-primary nav-auth-btn" onClick={onSignup}>Sign Up</button>
          </>
        ) : (
          <>
            <div className="live-clock" aria-live="off">
              {currentTime.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </div>
            <div className="profile-avatar-menu">
              <button
                className="profile-avatar-button"
                onClick={onToggleProfileView}
                aria-pressed={activeProfileView === 'profile'}
              >
                <img src={avatarUrl} alt="" className="profile-avatar-image" />
                <span className="profile-avatar-label">{displayName(user)}</span>
              </button>
            </div>
            <button className="btn-flat-secondary nav-auth-btn" onClick={onLogout}>Log Out</button>
          </>
        )}
      </div>
    </header>
  );
}
