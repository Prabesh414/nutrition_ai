/** The health-profile field set, shared by first-time setup and later edits. */
import type {
  ActivityLevel,
  DietaryPreference,
  FitnessGoal,
  Gender,
  ProfileInput,
} from '../api/types';
import { ACTIVITY_LEVELS, DIETARY_PREFERENCES, FITNESS_GOALS } from '../api/types';
import { DEFAULT_PROFILE } from '../lib/profile';

const GENDERS: readonly Gender[] = ['Male', 'Female', 'Other'];

interface ProfileFieldsProps {
  value: ProfileInput;
  onChange: (value: ProfileInput) => void;
  layout: 'grid' | 'stacked';
}

export function ProfileFields({ value, onChange, layout }: ProfileFieldsProps) {
  const set = <K extends keyof ProfileInput>(key: K, next: ProfileInput[K]) =>
    onChange({ ...value, [key]: next });

  const containerClass = layout === 'grid' ? 'profile-form-grid' : 'profile-edit-inline-grid';

  return (
    <div className={containerClass}>
      <div className="form-field-container">
        <label htmlFor="profile-age">Age (years)</label>
        <input
          id="profile-age" type="number" required className="form-input" min={13} max={120}
          value={value.age}
          onChange={(event) => set('age', parseInt(event.target.value, 10) || DEFAULT_PROFILE.age)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="profile-gender">Gender</label>
        <select
          id="profile-gender" className="form-input" value={value.gender}
          onChange={(event) => set('gender', event.target.value as Gender)}
        >
          {GENDERS.map((option) => <option key={option}>{option}</option>)}
        </select>
      </div>

      <div className="form-field-container">
        <label htmlFor="profile-height">Height (cm)</label>
        <input
          id="profile-height" type="number" required className="form-input" min={50} max={280}
          value={value.height}
          onChange={(event) => set('height', parseFloat(event.target.value) || DEFAULT_PROFILE.height)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="profile-weight">Weight (kg)</label>
        <input
          id="profile-weight" type="number" required className="form-input" min={20} max={500}
          value={value.weight}
          onChange={(event) => set('weight', parseFloat(event.target.value) || DEFAULT_PROFILE.weight)}
        />
      </div>

      <div className="form-field-container">
        <label htmlFor="profile-activity">Activity Level</label>
        <select
          id="profile-activity" className="form-input" value={value.activity_level}
          onChange={(event) => set('activity_level', event.target.value as ActivityLevel)}
        >
          {ACTIVITY_LEVELS.map((option) => <option key={option}>{option}</option>)}
        </select>
      </div>

      <div className="form-field-container">
        <label htmlFor="profile-goal">Fitness Goal</label>
        <select
          id="profile-goal" className="form-input" value={value.fitness_goal}
          onChange={(event) => set('fitness_goal', event.target.value as FitnessGoal)}
        >
          {FITNESS_GOALS.map((option) => <option key={option}>{option}</option>)}
        </select>
      </div>

      <div className="form-field-container">
        <label htmlFor="profile-diet">Dietary Preference</label>
        <select
          id="profile-diet" className="form-input" value={value.dietary_preference}
          onChange={(event) => set('dietary_preference', event.target.value as DietaryPreference)}
        >
          {DIETARY_PREFERENCES.map((option) => <option key={option}>{option}</option>)}
        </select>
      </div>
    </div>
  );
}
