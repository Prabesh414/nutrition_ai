import { useEffect, useRef, useState } from 'react';

import type { Coach as CoachState } from '../hooks/useCoach';
import { useDraggable } from '../hooks/useDraggable';

function MessageList({ messages, pending }: { messages: CoachState['messages']; pending: boolean }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pending]);

  return (
    <>
      {messages.map((message, index) => (
        <div
          key={index}
          className={`chat-bubble ${message.sender === 'user' ? 'user-bubble' : 'coach-bubble'}`}
        >
          {message.text}
        </div>
      ))}
      {pending && <div className="chat-bubble coach-bubble chat-typing">Thinking…</div>}
      <div ref={endRef} />
    </>
  );
}

function ChatForm({
  coach,
  placeholder,
  formClassName,
  inputClassName,
  buttonClassName,
}: {
  coach: CoachState;
  placeholder: string;
  formClassName: string;
  inputClassName: string;
  buttonClassName: string;
}) {
  const [draft, setDraft] = useState('');

  return (
    <form
      className={formClassName}
      onSubmit={(event) => {
        event.preventDefault();
        const message = draft;
        setDraft('');
        void coach.send(message);
      }}
    >
      <input
        type="text"
        className={inputClassName}
        placeholder={placeholder}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        aria-label="Message the nutrition coach"
      />
      <button type="submit" className={buttonClassName} disabled={coach.pending || !draft.trim()}>
        Send
      </button>
    </form>
  );
}

export function CoachPanel({ coach }: { coach: CoachState }) {
  return (
    <div className="coach-tab-container">
      <div className="dashboard-card chatbot-card">
        <h3>AI Nutrition Assistant</h3>
        <div className="chatbot-chatbox">
          <MessageList messages={coach.messages} pending={coach.pending} />
        </div>
        <ChatForm
          coach={coach}
          placeholder="Ask about your targets, meals, protein..."
          formClassName="chatbot-input-form"
          inputClassName="chat-input"
          buttonClassName="btn-flat-primary chat-send-btn"
        />
      </div>
    </div>
  );
}

export function FloatingCoach({ coach }: { coach: CoachState }) {
  const [open, setOpen] = useState(false);
  const { position, dragging, onPointerDown } = useDraggable(() => setOpen((value) => !value));

  const popupStyle: React.CSSProperties = {
    position: 'absolute',
    width: '340px',
    height: '450px',
    pointerEvents: 'auto',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 1001,
    ...(position.y < 500 ? { top: '65px' } : { bottom: '65px' }),
    ...(position.x < 350 ? { left: 0 } : { right: 0 }),
  };

  return (
    <div className="floating-bot-wrapper" style={{ left: `${position.x}px`, top: `${position.y}px` }}>
      <button
        type="button"
        className={`floating-bot-trigger ${open ? 'active' : ''}`}
        onPointerDown={onPointerDown}
        title="AI Nutrition Coach (drag to move, click to chat)"
        aria-label="Open the nutrition coach"
        aria-expanded={open}
        style={{ cursor: dragging ? 'grabbing' : 'grab', touchAction: 'none' }}
      >
        <svg
          width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
        >
          <rect width="18" height="12" x="3" y="8" rx="2" ry="2" />
          <path d="M12 2v6" />
          <path d="M8 2h8" />
          <path d="M12 18v2" />
          <path d="M8 20h8" />
          <circle cx="8" cy="13" r="1" />
          <circle cx="16" cy="13" r="1" />
        </svg>
      </button>

      {open && (
        <div className="floating-chat-popup" style={popupStyle}>
          <div className="floating-chat-header">
            <div className="floating-chat-title">
              <span className="dot-active" />
              AI Nutrition Coach
            </div>
            <button
              type="button"
              className="floating-chat-close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              ×
            </button>
          </div>
          <div className="floating-chat-messages">
            <MessageList messages={coach.messages} pending={coach.pending} />
          </div>
          <ChatForm
            coach={coach}
            placeholder="Ask your coach anything..."
            formClassName="floating-chat-input-form"
            inputClassName="floating-chat-input"
            buttonClassName="floating-chat-send-btn"
          />
        </div>
      )}
    </div>
  );
}
