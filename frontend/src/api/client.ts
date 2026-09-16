/**
 * Typed API client.
 *
 * Every request carries the bearer token; the server derives the user from it.
 * Previously the frontend put the user's email in the URL or body and the
 * server trusted whatever arrived.
 */
import type {
  ApiAuthResponse,
  ApiChatResponse,
  ApiDailySummary,
  ApiFood,
  ApiMeal,
  ApiProfile,
  ApiRecommendationsResponse,
  ApiUser,
  MealInput,
  ProfileInput,
} from './types';

export const API_BASE_URL: string =
  import.meta.env.VITE_API_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;

const TOKEN_STORAGE_KEY = 'nutrition_ai_token';

/** An HTTP error carrying the status so callers can branch on 401. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null; // Private browsing or blocked storage.
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Non-fatal: the session simply will not survive a reload.
  }
}

/** Invoked on any 401 so the app can drop to a logged-out state. */
let unauthorizedHandler: (() => void) | null = null;

export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler;
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  signal?: AbortSignal;
}

function extractDetail(payload: unknown, fallback: string): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    // FastAPI validation errors arrive as a list of objects.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown; loc?: unknown };
      const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]) : '';
      const message = typeof first.msg === 'string' ? first.msg : fallback;
      return field ? `${field}: ${message}` : message;
    }
  }
  return fallback;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, signal } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('Cannot reach the server. Is the backend running?', 0);
  }

  if (response.status === 401 && auth) {
    setToken(null);
    unauthorizedHandler?.();
    throw new ApiError('Your session has expired. Please log in again.', 401);
  }

  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(extractDetail(payload, `Request failed (${response.status})`), response.status);
  }

  return payload as T;
}

export const api = {
  register(input: {
    first_name: string;
    middle_name?: string | null;
    last_name: string;
    email: string;
    password: string;
  }): Promise<ApiAuthResponse> {
    return request<ApiAuthResponse>('/auth/register', { method: 'POST', body: input, auth: false });
  },

  login(email: string, password: string): Promise<ApiAuthResponse> {
    return request<ApiAuthResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
    });
  },

  me(): Promise<ApiUser> {
    return request<ApiUser>('/auth/me');
  },

  saveProfile(input: ProfileInput): Promise<ApiProfile> {
    return request<ApiProfile>('/profile', { method: 'PUT', body: input });
  },

  listMeals(logDate?: string): Promise<ApiMeal[]> {
    return request<ApiMeal[]>(`/meals${logDate ? `?log_date=${logDate}` : ''}`);
  },

  dailySummary(logDate?: string): Promise<ApiDailySummary> {
    return request<ApiDailySummary>(`/meals/summary${logDate ? `?log_date=${logDate}` : ''}`);
  },

  addMeal(input: MealInput): Promise<ApiMeal> {
    return request<ApiMeal>('/meals', { method: 'POST', body: input });
  },

  deleteMeal(mealId: number): Promise<void> {
    return request<void>(`/meals/${mealId}`, { method: 'DELETE' });
  },

  searchFoods(query: string, signal?: AbortSignal): Promise<ApiFood[]> {
    return request<ApiFood[]>(`/foods?query=${encodeURIComponent(query)}`, { auth: false, signal });
  },

  recommendations(signal?: AbortSignal): Promise<ApiRecommendationsResponse> {
    return request<ApiRecommendationsResponse>('/recommendations', { signal });
  },

  chat(message: string): Promise<ApiChatResponse> {
    return request<ApiChatResponse>('/chat', { method: 'POST', body: { message } });
  },
};

/** Today's date as YYYY-MM-DD in the *browser's* timezone, not UTC. */
export function localDateString(date: Date = new Date()): string {
  const offsetMinutes = date.getTimezoneOffset();
  return new Date(date.getTime() - offsetMinutes * 60_000).toISOString().slice(0, 10);
}
