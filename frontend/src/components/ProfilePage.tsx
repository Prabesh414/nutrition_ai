import { useState } from 'react';

import type { ApiProfile, ApiUser, ProfileInput } from '../api/types';
import { MAX_PROFILE_IMAGE_BYTES, readImageAsDataUrl } from '../lib/image';
import { ProfileFields } from './ProfileForm';
import { profileToInput, useProfileSubmit } from '../lib/profile';

interface ProfilePageProps {
  user: ApiUser;
  profile: ApiProfile | null;
  avatarUrl: string;
  onSaveProfile: (input: ProfileInput) => Promise<void>;
  onBackToDashboard: () => void;
  onOpenCoach: () => void;
}

export function ProfilePage({
  user,
  profile,
  avatarUrl,
  onSaveProfile,
  onBackToDashboard,
  onOpenCoach,
}: ProfilePageProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ProfileInput>(() => profileToInput(profile));
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const { saving, error, submit } = useProfileSubmit(onSaveProfile);

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setAvatarError(null);
    try {
      const dataUrl = await readImageAsDataUrl(file);
      await onSaveProfile({ ...profileToInput(profile), profile_image_url: dataUrl });
    } catch (caught) {
      setAvatarError(caught instanceof Error ? caught.message : 'Could not save that image.');
    }
  };

  return (
    <div className="profile-page">
      <div className="dashboard-card profile-header-card">
        <div className="profile-header-top">
          <div className="profile-avatar-region">
            <div className="profile-avatar-large-wrap">
              <img src={avatarUrl} alt="" className="profile-avatar-large" />
            </div>
            <label className="upload-photo-button" title="Upload profile photo">
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden-upload-input"
                onChange={handleAvatarUpload}
              />
              <span>Upload Photo</span>
            </label>
            <span className="upload-hint">
              PNG or JPEG, up to {Math.round(MAX_PROFILE_IMAGE_BYTES / 1024)} KB
            </span>
          </div>
          <div>
            <p className="profile-kicker">Your Profile</p>
            <h2>{user.email}</h2>
          </div>
        </div>

        {avatarError && <p className="form-error">{avatarError}</p>}

        <div className="profile-mini-grid">
          <div className="mini-stat"><span>Age:</span><strong>{profile?.age ?? '—'}</strong></div>
          <div className="mini-stat"><span>Height:</span><strong>{profile?.height ?? '—'} cm</strong></div>
          <div className="mini-stat"><span>Weight:</span><strong>{profile?.weight ?? '—'} kg</strong></div>
          <div className="mini-stat"><span>Goal:</span><strong>{profile?.fitness_goal ?? 'Set a goal'}</strong></div>
        </div>
      </div>

      <div className="profile-grid">
        <div className="dashboard-card profile-detail-card">
          {editing ? (
            <form
              className="profile-edit-inline-form"
              onSubmit={(event) => {
                event.preventDefault();
                void submit(draft, () => setEditing(false));
              }}
            >
              <h3>Edit Health Metrics</h3>
              <ProfileFields value={draft} onChange={setDraft} layout="stacked" />
              {error && <p className="form-error">{error}</p>}
              <div className="profile-edit-inline-actions">
                <button type="submit" className="btn-flat-primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button
                  type="button"
                  className="btn-flat-secondary"
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <>
              <h3>Health Snapshot</h3>
              <ul className="profile-detail-list">
                <li><span>BMI:</span><strong>{profile?.bmi ?? '—'}</strong></li>
                <li><span>BMR:</span><strong>{profile?.bmr ?? '—'} kcal</strong></li>
                <li><span>Activity:</span><strong>{profile?.activity_level ?? 'Not set'}</strong></li>
                <li><span>Diet:</span><strong>{profile?.dietary_preference ?? 'Not set'}</strong></li>
                <li><span>Target Calories:</span><strong>{profile?.target_calories ?? '—'} kcal</strong></li>
                <li><span>Target Protein:</span><strong>{profile?.target_protein ?? '—'} g</strong></li>
              </ul>
              <button
                type="button"
                className="btn-flat-secondary edit-profile-btn"
                onClick={() => {
                  setDraft(profileToInput(profile));
                  setEditing(true);
                }}
              >
                Edit Health Details
              </button>
            </>
          )}
        </div>

        <div className="dashboard-card usage-card">
          <h3>How your targets are calculated</h3>
          <p className="usage-note">
            Your BMR uses the Mifflin-St Jeor equation, multiplied by an activity factor to give
            your daily energy expenditure. Your goal then adjusts that by 500 kcal, and the macro
            split follows your goal. All of it is computed on the server from the details above.
          </p>
          <div className="usage-summary-grid">
            <div className="usage-tile">
              <span>Daily Budget</span>
              <strong>{profile?.target_calories ?? '—'} kcal</strong>
            </div>
            <div className="usage-tile">
              <span>Protein / Carbs / Fat</span>
              <strong>
                {profile ? `${profile.target_protein} / ${profile.target_carbs} / ${profile.target_fat} g` : '—'}
              </strong>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-card profile-action-card">
        <h3>Profile Actions</h3>
        <div className="profile-actions-row">
          <button className="btn-flat-primary" onClick={onBackToDashboard}>Back to Dashboard</button>
          <button className="btn-flat-secondary" onClick={onOpenCoach}>Open AI Coach</button>
        </div>
      </div>
    </div>
  );
}
