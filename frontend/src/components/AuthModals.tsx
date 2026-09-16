import { useState } from 'react';

import type { ProfileInput } from '../api/types';
import { ProfileFields } from './ProfileForm';
import { DEFAULT_PROFILE, useProfileSubmit } from '../lib/profile';

export type ModalKind = 'login' | 'signup' | 'profile' | null;

export interface SignupDraft {
  first_name: string;
  middle_name: string;
  last_name: string;
  email: string;
  password: string;
}

const EMPTY_SIGNUP: SignupDraft = {
  first_name: '',
  middle_name: '',
  last_name: '',
  email: '',
  password: '',
};

interface AuthModalsProps {
  modal: ModalKind;
  onClose: () => void;
  onSwitch: (modal: ModalKind) => void;
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (draft: SignupDraft) => Promise<void>;
  onSaveProfile: (input: ProfileInput) => Promise<void>;
}

function LoginForm({
  onLogin,
  onSwitch,
}: Pick<AuthModalsProps, 'onLogin' | 'onSwitch'>) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <form
      className="auth-form"
      onSubmit={async (event) => {
        event.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await onLogin(email, password);
        } catch (caught) {
          setError(caught instanceof Error ? caught.message : 'Login failed.');
        } finally {
          setBusy(false);
        }
      }}
    >
      <h2>Welcome Back</h2>
      <p>Log in to access your personal nutrition dashboard.</p>

      <div className="form-field-container">
        <label htmlFor="login-email">Email Address</label>
        <input
          id="login-email" type="email" required className="form-input"
          placeholder="name@example.com" autoComplete="email"
          value={email} onChange={(event) => setEmail(event.target.value)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password" type="password" required className="form-input"
          placeholder="••••••••" autoComplete="current-password"
          value={password} onChange={(event) => setPassword(event.target.value)}
        />
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-flat-primary auth-submit" disabled={busy}>
        {busy ? 'Logging in…' : 'Log In'}
      </button>
      <p className="auth-toggle-link">
        Don&apos;t have an account?{' '}
        <button type="button" className="link-button" onClick={() => onSwitch('signup')}>Sign Up</button>
      </p>
    </form>
  );
}

function SignupForm({
  onRegister,
  onSwitch,
}: Pick<AuthModalsProps, 'onRegister' | 'onSwitch'>) {
  const [draft, setDraft] = useState<SignupDraft>(EMPTY_SIGNUP);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: keyof SignupDraft, value: string) => setDraft({ ...draft, [key]: value });

  return (
    <form
      className="auth-form"
      onSubmit={async (event) => {
        event.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await onRegister(draft);
        } catch (caught) {
          setError(caught instanceof Error ? caught.message : 'Registration failed.');
        } finally {
          setBusy(false);
        }
      }}
    >
      <h2>Create Account</h2>
      <p>Build your profile and get personalized nutrition calculations.</p>

      <div className="form-field-container">
        <label htmlFor="signup-first">First Name</label>
        <input
          id="signup-first" type="text" required className="form-input" placeholder="First name"
          autoComplete="given-name"
          value={draft.first_name} onChange={(event) => set('first_name', event.target.value)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="signup-middle">Middle Name (optional)</label>
        <input
          id="signup-middle" type="text" className="form-input" placeholder="Middle name"
          autoComplete="additional-name"
          value={draft.middle_name} onChange={(event) => set('middle_name', event.target.value)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="signup-last">Last Name</label>
        <input
          id="signup-last" type="text" required className="form-input" placeholder="Last name"
          autoComplete="family-name"
          value={draft.last_name} onChange={(event) => set('last_name', event.target.value)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="signup-email">Email Address</label>
        <input
          id="signup-email" type="email" required className="form-input"
          placeholder="name@example.com" autoComplete="email"
          value={draft.email} onChange={(event) => set('email', event.target.value)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="signup-password">Password</label>
        <input
          id="signup-password" type="password" required minLength={8} className="form-input"
          placeholder="At least 8 characters" autoComplete="new-password"
          value={draft.password} onChange={(event) => set('password', event.target.value)}
        />
        <small className="field-hint">Must be at least 8 characters.</small>
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-flat-primary auth-submit" disabled={busy}>
        {busy ? 'Creating account…' : 'Continue to Profile Setup'}
      </button>
      <p className="auth-toggle-link">
        Already have an account?{' '}
        <button type="button" className="link-button" onClick={() => onSwitch('login')}>Log In</button>
      </p>
    </form>
  );
}

function ProfileSetupForm({ onSaveProfile, onClose }: Pick<AuthModalsProps, 'onSaveProfile' | 'onClose'>) {
  const [draft, setDraft] = useState<ProfileInput>({ ...DEFAULT_PROFILE });
  const { saving, error, submit } = useProfileSubmit(onSaveProfile);

  return (
    <form
      className="auth-form profile-setup-form"
      onSubmit={(event) => {
        event.preventDefault();
        void submit(draft, onClose);
      }}
    >
      <h2>Health Profile</h2>
      <p>Provide your details to calculate your BMI, BMR and daily macro budgets.</p>

      <ProfileFields value={draft} onChange={setDraft} layout="grid" />

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-flat-primary auth-submit" disabled={saving}>
        {saving ? 'Calculating…' : 'Generate Dashboard & Targets'}
      </button>
    </form>
  );
}

export function AuthModals({
  modal,
  onClose,
  onSwitch,
  onLogin,
  onRegister,
  onSaveProfile,
}: AuthModalsProps) {
  if (!modal) return null;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-box">
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        {modal === 'login' && <LoginForm onLogin={onLogin} onSwitch={onSwitch} />}
        {modal === 'signup' && <SignupForm onRegister={onRegister} onSwitch={onSwitch} />}
        {modal === 'profile' && <ProfileSetupForm onSaveProfile={onSaveProfile} onClose={onClose} />}
      </div>
    </div>
  );
}
