import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import MessageBubble from './MessageBubble';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content: `👋 Welcome to **FleetPulse AI**! I'm your intelligent IT operations assistant.

I can help you with:
- **Fleet Risk Assessment** — "Which devices in Sales need attention this week?"
- **Device Health Check** — "What's the battery status on DEV-A3F2C8?"
- **Repair Information** — "What replacement battery does the iPhone 13 need?"
- **Remediation Tickets** — "Create a ticket for the failing Galaxy S24 battery"

How can I help you manage your device fleet today?`,
};

const SUGGESTED_QUERIES = [
  'Which devices need attention this week?',
  'Show me all critical risk devices',
  'What\'s the fleet health overview?',
  'Look up battery replacement for iPhone 13',
];

export default function ChatPanel() {
  const { messages, isLoading, sendMessage, clearChat } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const allMessages = [WELCOME_MESSAGE, ...messages];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestion = (query) => {
    setInput(query);
    sendMessage(query);
    setInput('');
  };

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <h2>💬 AI Assistant</h2>
        <button
          onClick={clearChat}
          style={{
            background: 'transparent',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-secondary)',
            padding: '4px 12px',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            fontSize: 'var(--font-size-xs)',
            transition: 'all var(--transition-fast)',
          }}
          onMouseOver={e => e.target.style.borderColor = 'var(--color-border-hover)'}
          onMouseOut={e => e.target.style.borderColor = 'var(--color-border)'}
        >
          Clear Chat
        </button>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {allMessages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* Typing indicator */}
        {isLoading && !messages.some(m => m.isStreaming) && (
          <div className="message assistant">
            <div className="message-avatar">⚡</div>
            <div className="message-content">
              <div className="typing-indicator">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            </div>
          </div>
        )}

        {/* Suggestions (show only when no messages yet) */}
        {messages.length === 0 && (
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--space-sm)',
            marginTop: 'var(--space-md)',
            justifyContent: 'center',
          }}>
            {SUGGESTED_QUERIES.map((query, i) => (
              <button
                key={i}
                onClick={() => handleSuggestion(query)}
                style={{
                  background: 'var(--color-bg-glass)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-secondary)',
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-full)',
                  cursor: 'pointer',
                  fontSize: 'var(--font-size-xs)',
                  transition: 'all var(--transition-fast)',
                  whiteSpace: 'nowrap',
                }}
                onMouseOver={e => {
                  e.target.style.borderColor = 'var(--color-accent-blue)';
                  e.target.style.color = 'var(--color-accent-blue)';
                }}
                onMouseOut={e => {
                  e.target.style.borderColor = 'var(--color-border)';
                  e.target.style.color = 'var(--color-text-secondary)';
                }}
              >
                {query}
              </button>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your device fleet..."
            rows={1}
            disabled={isLoading}
          />
          <button
            className="chat-send-btn"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
          >
            {isLoading ? '...' : 'Send'}
          </button>
        </div>
        <div style={{
          marginTop: 'var(--space-xs)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-text-muted)',
          textAlign: 'center',
        }}>
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
