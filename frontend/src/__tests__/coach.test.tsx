import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useCoach } from '../hooks/useCoach';
import { api } from '../api/client';

describe('useCoach', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('starts with a single greeting from the coach', () => {
    const { result } = renderHook(() => useCoach());
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].sender).toBe('coach');
  });

  it('appends the question and the reply in order', async () => {
    vi.spyOn(api, 'chat').mockResolvedValue({ reply: 'Aim for 110g.', source: 'rules' });
    const { result } = renderHook(() => useCoach());

    await act(async () => { await result.current.send('how much protein?'); });

    await waitFor(() => expect(result.current.messages).toHaveLength(3));
    expect(result.current.messages[1]).toEqual({ sender: 'user', text: 'how much protein?' });
    expect(result.current.messages[2]).toEqual({ sender: 'coach', text: 'Aim for 110g.' });
  });

  it('ignores blank input', async () => {
    const spy = vi.spyOn(api, 'chat');
    const { result } = renderHook(() => useCoach());

    await act(async () => { await result.current.send('   '); });

    expect(spy).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(1);
  });

  it('shows a failure as a coach message rather than throwing', async () => {
    vi.spyOn(api, 'chat').mockRejectedValue(new Error('Cannot reach the server.'));
    const { result } = renderHook(() => useCoach());

    await act(async () => { await result.current.send('hello'); });

    await waitFor(() => expect(result.current.messages).toHaveLength(3));
    expect(result.current.messages[2].text).toMatch(/Cannot reach the server/);
    expect(result.current.pending).toBe(false);
  });
});
