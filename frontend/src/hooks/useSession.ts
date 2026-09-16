/** Authentication session: the bearer token and the user it belongs to. */
import { useCallback, useEffect, useState } from 'react';

import { ApiError, api, getToken, onUnauthorized, setToken } from '../api/client';
import type { ApiAuthResponse, ApiUser, ProfileInput } from '../api/types';

export interface Session {
  user: ApiUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    first_name: string;
    middle_name?: string | null;
    last_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  saveProfile: (input: ProfileInput) => Promise<void>;
  logout: () => void;
}

export function useSession(): Session {
  const [user, setUser] = useState<ApiUser | null>(null);
  // Start in a loading state only when a token exists to be validated.
  const [loading, setLoading] = useState<boolean>(() => getToken() !== null);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  // A 401 from any request drops the session instead of leaving a stale user
  // on screen whose every action silently fails.
  useEffect(() => {
    onUnauthorized(() => setUser(null));
  }, []);

  // Restore the session on load by validating the stored token against the
  // server, rather than trusting a user object cached in localStorage.
  useEffect(() => {
    if (getToken() === null) return;

    let cancelled = false;
    api
      .me()
      .then((restored) => {
        if (!cancelled) setUser(restored);
      })
      .catch(() => {
        if (!cancelled) setToken(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const adopt = useCallback((response: ApiAuthResponse) => {
    setToken(response.access_token);
    setUser(response.user);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      adopt(await api.login(email, password));
    },
    [adopt],
  );

  const register = useCallback(
    async (input: Parameters<Session['register']>[0]) => {
      adopt(await api.register(input));
    },
    [adopt],
  );

  const saveProfile = useCallback(async (input: ProfileInput) => {
    const profile = await api.saveProfile(input);
    setUser((previous) => (previous ? { ...previous, profile } : previous));
  }, []);

  return { user, loading, login, register, saveProfile, logout };
}

export function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}

export function displayName(user: ApiUser): string {
  const parts = [user.first_name, user.middle_name, user.last_name].filter(Boolean);
  return parts.join(' ') || user.username || user.email.split('@')[0];
}
