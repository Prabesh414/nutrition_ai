/**
 * Nutrition coach conversation.
 *
 * Shared by the dashboard tab and the floating widget, which each carried their
 * own duplicated copy of a hardcoded if/else "AI". Replies now come from the
 * backend, which uses an LLM when available and rule-based answers otherwise.
 */
import { useCallback, useState } from 'react';

import { api } from '../api/client';

export interface ChatMessage {
  sender: 'user' | 'coach';
  text: string;
}

const GREETING: ChatMessage = {
  sender: 'coach',
  text: 'Hi! I am your nutrition coach. Ask me about your targets, your meals, or anything nutrition related.',
};

export interface Coach {
  messages: ChatMessage[];
  pending: boolean;
  send: (message: string) => Promise<void>;
}

export function useCoach(): Coach {
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [pending, setPending] = useState(false);

  const send = useCallback(async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed || pending) return;

    setMessages((previous) => [...previous, { sender: 'user', text: trimmed }]);
    setPending(true);

    try {
      const response = await api.chat(trimmed);
      setMessages((previous) => [...previous, { sender: 'coach', text: response.reply }]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          sender: 'coach',
          text:
            error instanceof Error
              ? `Sorry, I could not answer that: ${error.message}`
              : 'Sorry, I could not answer that right now.',
        },
      ]);
    } finally {
      setPending(false);
    }
  }, [pending]);

  return { messages, pending, send };
}
