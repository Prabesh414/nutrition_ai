/** Profile form helpers, kept out of the component file so fast refresh works. */
import { useState } from 'react';

import type { ApiProfile, ProfileInput } from '../api/types';

export const DEFAULT_PROFILE: ProfileInput = {
  age: 25,
  gender: 'Male',
  height: 175,
  weight: 70,
  activity_level: 'Moderately Active',
  fitness_goal: 'Maintain Weight',
  dietary_preference: 'None',
};

export function profileToInput(profile: ApiProfile | null): ProfileInput {
  if (!profile) return { ...DEFAULT_PROFILE };
  return {
    age: profile.age,
    gender: profile.gender,
    height: profile.height,
    weight: profile.weight,
    activity_level: profile.activity_level,
    fitness_goal: profile.fitness_goal,
    dietary_preference: profile.dietary_preference,
  };
}

/** Tracks submission state for any profile form so errors surface in the UI. */
export function useProfileSubmit(save: (input: ProfileInput) => Promise<void>) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (input: ProfileInput, onDone?: () => void) => {
    setSaving(true);
    setError(null);
    try {
      await save(input);
      onDone?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save your profile.');
    } finally {
      setSaving(false);
    }
  };

  return { saving, error, submit };
}
