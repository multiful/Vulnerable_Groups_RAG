// Content Hash: SHA256:TBD
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { MessageCircle, X, Send, Bot } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Props {
  context?: {
    stage_id?: string;
    domain_id?: string;
    cert_name?: string;
  };
}

const INITIAL_MESSAGES: Message[] = [
  {
    role: 'assistant',
    content: '안녕하세요! DIDIM 진로 상담사입니다. 자격증 추천, 로드맵, 취업 준비에 대해 무엇이든 물어보세요.',
  },
];

const ChatWidget: React.FC<Props> = ({ context = {} }) => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 120);
    }
  }, [open]);

  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, open]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { role: 'user', content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: nextMessages, context }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const reply: string =
        data?.reply ?? data?.content ?? data?.message ?? '응답을 받지 못했습니다.';
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.' },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, context]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <style>{`
        .chat-fab {
          position: fixed;
          bottom: 1.5rem;
          right: 1.5rem;
          z-index: 1000;
          width: 52px;
          height: 52px;
          border-radius: 50%;
          background: var(--primary);
          color: #fff;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 18px rgba(99,102,241,.35);
          transition: transform .15s, box-shadow .15s;
        }
        .chat-fab:hover {
          transform: scale(1.07);
          box-shadow: 0 6px 24px rgba(99,102,241,.45);
        }
        @media (max-width: 768px) {
          .chat-fab { bottom: calc(var(--mobile-nav-h, 56px) + 1rem); }
          .chat-panel { bottom: calc(var(--mobile-nav-h, 56px) + 4.5rem) !important; }
        }

        .chat-panel {
          position: fixed;
          bottom: 5.5rem;
          right: 1.5rem;
          z-index: 999;
          width: 380px;
          height: 520px;
          background: var(--surface, #fff);
          border: 1px solid var(--border, #e2e8f0);
          border-radius: var(--radius, 12px);
          box-shadow: 0 12px 40px rgba(15,23,42,.15);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          animation: chat-slide-up .18s ease;
        }
        @keyframes chat-slide-up {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: none; }
        }
        @media (max-width: 430px) {
          .chat-panel {
            width: calc(100vw - 2rem);
            right: 1rem;
          }
        }

        .chat-header {
          display: flex;
          align-items: center;
          gap: .5rem;
          padding: .75rem 1rem;
          background: var(--primary);
          color: #fff;
          flex-shrink: 0;
        }
        .chat-header-title {
          flex: 1;
          font-size: .875rem;
          font-weight: 700;
          letter-spacing: -.01em;
        }
        .chat-close-btn {
          background: none;
          border: none;
          cursor: pointer;
          color: rgba(255,255,255,.8);
          display: flex;
          align-items: center;
          padding: .2rem;
          border-radius: var(--radius-xs, 4px);
          transition: color .12s;
        }
        .chat-close-btn:hover { color: #fff; }

        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: .75rem;
          display: flex;
          flex-direction: column;
          gap: .625rem;
          background: var(--surface-2, #f8fafc);
        }
        .chat-messages::-webkit-scrollbar { width: 4px; }
        .chat-messages::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

        .chat-bubble-wrap {
          display: flex;
          gap: .4rem;
          align-items: flex-end;
        }
        .chat-bubble-wrap.user { flex-direction: row-reverse; }

        .chat-avatar {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: var(--primary);
          color: #fff;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .chat-bubble {
          max-width: 75%;
          padding: .5rem .75rem;
          border-radius: var(--radius-sm, 8px);
          font-size: .82rem;
          line-height: 1.55;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .chat-bubble.assistant {
          background: #fff;
          border: 1px solid var(--border, #e2e8f0);
          color: var(--text, #1e293b);
          border-bottom-left-radius: 4px;
        }
        .chat-bubble.user {
          background: var(--primary);
          color: #fff;
          border-bottom-right-radius: 4px;
        }

        .chat-typing {
          display: flex;
          align-items: center;
          gap: .3rem;
          padding: .4rem .75rem;
        }
        .chat-typing-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--text-muted, #94a3b8);
          animation: chat-bounce .9s infinite;
        }
        .chat-typing-dot:nth-child(2) { animation-delay: .15s; }
        .chat-typing-dot:nth-child(3) { animation-delay: .3s; }
        @keyframes chat-bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-5px); }
        }

        .chat-input-row {
          display: flex;
          gap: .5rem;
          padding: .625rem .75rem;
          border-top: 1px solid var(--border, #e2e8f0);
          background: var(--surface, #fff);
          flex-shrink: 0;
        }
        .chat-input {
          flex: 1;
          border: 1px solid var(--border, #e2e8f0);
          border-radius: var(--radius-sm, 8px);
          padding: .45rem .75rem;
          font-size: .82rem;
          font-family: inherit;
          color: var(--text, #1e293b);
          background: var(--surface-2, #f8fafc);
          outline: none;
          transition: border-color .15s;
        }
        .chat-input:focus { border-color: var(--primary); }
        .chat-input::placeholder { color: var(--text-muted, #94a3b8); }
        .chat-send-btn {
          width: 36px;
          height: 36px;
          border-radius: var(--radius-sm, 8px);
          background: var(--primary);
          color: #fff;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          transition: opacity .15s;
        }
        .chat-send-btn:disabled { opacity: .45; cursor: not-allowed; }
        .chat-send-btn:not(:disabled):hover { opacity: .88; }
      `}</style>

      {/* FAB button */}
      <button
        type="button"
        className="chat-fab"
        aria-label={open ? '채팅 닫기' : '상담 채팅 열기'}
        onClick={() => setOpen(o => !o)}
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="chat-panel" role="dialog" aria-label="DIDIM 상담 채팅">
          {/* Header */}
          <div className="chat-header">
            <Bot size={18} />
            <span className="chat-header-title">DIDIM 상담</span>
            <button
              type="button"
              className="chat-close-btn"
              aria-label="채팅 닫기"
              onClick={() => setOpen(false)}
            >
              <X size={18} />
            </button>
          </div>

          {/* Messages */}
          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-bubble-wrap ${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div className="chat-avatar">
                    <Bot size={14} />
                  </div>
                )}
                <div className={`chat-bubble ${msg.role}`}>{msg.content}</div>
              </div>
            ))}
            {loading && (
              <div className="chat-bubble-wrap assistant">
                <div className="chat-avatar"><Bot size={14} /></div>
                <div className="chat-bubble assistant chat-typing">
                  <span className="chat-typing-dot" />
                  <span className="chat-typing-dot" />
                  <span className="chat-typing-dot" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="chat-input-row">
            <input
              ref={inputRef}
              type="text"
              className="chat-input"
              placeholder="메시지를 입력하세요…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              maxLength={500}
            />
            <button
              type="button"
              className="chat-send-btn"
              aria-label="전송"
              onClick={sendMessage}
              disabled={loading || !input.trim()}
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default ChatWidget;
