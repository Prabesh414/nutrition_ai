import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, api, getToken, localDateString, onUnauthorized, setToken } from '../api/client';

function mockFetch(status: number, body: unknown) {
  const response = {
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  } as Response;
  // Typed with fetch's signature so `spy.mock.calls[n][1]` narrows to RequestInit.
  const spy = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => response);
  vi.stubGlobal('fetch', spy);
  return spy;
}

function headersOf(init: RequestInit | undefined): Record<string, string> {
  return (init?.headers ?? {}) as Record<string, string>;
}

describe('token storage', () => {
  beforeEach(() => localStorage.clear());

  it('round-trips a token', () => {
    setToken('abc123');
    expect(getToken()).toBe('abc123');
    setToken(null);
    expect(getToken()).toBeNull();
  });
});

describe('request handling', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('attaches the bearer token to authenticated calls', async () => {
    setToken('my-token');
    const spy = mockFetch(200, []);

    await api.listMeals();

    expect(headersOf(spy.mock.calls[0][1]).Authorization).toBe('Bearer my-token');
  });

  it('does not send a token to public endpoints', async () => {
    setToken('my-token');
    const spy = mockFetch(200, []);

    await api.searchFoods('oats');

    expect(headersOf(spy.mock.calls[0][1]).Authorization).toBeUndefined();
  });

  it('clears the session and notifies on 401', async () => {
    setToken('stale-token');
    const handler = vi.fn();
    onUnauthorized(handler);
    mockFetch(401, { detail: 'Could not validate credentials' });

    await expect(api.listMeals()).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
    expect(handler).toHaveBeenCalled();
  });

  it('surfaces a plain string detail', async () => {
    mockFetch(409, { detail: 'User already exists' });

    await expect(
      api.register({ first_name: 'A', last_name: 'B', email: 'a@b.com', password: 'longenough' }),
    ).rejects.toThrow('User already exists');
  });

  it('flattens a FastAPI validation error into something readable', async () => {
    mockFetch(422, {
      detail: [{ loc: ['body', 'password'], msg: 'String should have at least 8 characters' }],
    });

    await expect(
      api.register({ first_name: 'A', last_name: 'B', email: 'a@b.com', password: 'short' }),
    ).rejects.toThrow('password: String should have at least 8 characters');
  });

  it('reports an unreachable server rather than throwing a raw TypeError', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch'); }));

    await expect(api.searchFoods('oats')).rejects.toThrow(/Cannot reach the server/);
  });

  it('treats 204 as success with no body', async () => {
    setToken('t');
    mockFetch(204, null);
    await expect(api.deleteMeal(1)).resolves.toBeUndefined();
  });
});

describe('localDateString', () => {
  it('uses the local calendar day, not the UTC day', () => {
    // 00:30 local on the 2nd must stay the 2nd even when UTC is still the 1st.
    const localMidnightish = new Date(2026, 8, 2, 0, 30, 0);
    expect(localDateString(localMidnightish)).toBe('2026-09-02');
  });

  it('formats as YYYY-MM-DD', () => {
    expect(localDateString(new Date(2026, 0, 5, 12))).toBe('2026-01-05');
  });
});
