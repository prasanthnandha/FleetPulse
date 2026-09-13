import React from 'react';
import PartInfo from './PartInfo';
import TicketPreview from './TicketPreview';

const RISK_EMOJI = {
  healthy: '🟢',
  watch: '🟡',
  warning: '🟠',
  critical: '🔴',
};

function formatToolName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

export default function MessageBubble({ message }) {
  const { role, content, toolCalls, toolResults, isStreaming, isError } = message;
  const isUser = role === 'user';

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '⚡'}
      </div>
      <div className="message-content">
        {/* Tool calls */}
        {toolCalls && toolCalls.length > 0 && (
          <div style={{ marginBottom: 'var(--space-sm)' }}>
            {toolCalls.map((tc, i) => (
              <div key={i} className={`tool-indicator ${toolResults?.[i] ? 'done' : ''}`}>
                <span>🔧</span>
                <span>{formatToolName(tc.tool)}</span>
                {tc.arguments?.fleet_name && <span>• {tc.arguments.fleet_name}</span>}
                {tc.arguments?.device_model && <span>• {tc.arguments.device_model}</span>}
              </div>
            ))}
          </div>
        )}

        {/* Rich Cards for Tool Results */}
        {toolResults && toolResults.length > 0 && (
          <div style={{ marginBottom: 'var(--space-sm)' }}>
            {toolResults.map((tr, i) => {
              if (!tr) return null;
              if (tr.ticket_id) {
                return <TicketPreview key={`ticket-${i}`} ticket={tr} />;
              }
              if (tr.part_number || tr.safety_warnings || (tr.found !== undefined && tr.device_model)) {
                return <PartInfo key={`part-${i}`} partData={tr} />;
              }
              return null;
            })}
          </div>
        )}

        {/* Main content */}
        <div style={{ color: isError ? 'var(--color-critical)' : undefined }}>
          {content ? renderContent(content) : isStreaming ? (
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          ) : null}
        </div>

        {/* Streaming cursor */}
        {isStreaming && content && (
          <span style={{
            display: 'inline-block',
            width: '2px',
            height: '1em',
            background: 'var(--color-accent-blue)',
            marginLeft: '2px',
            animation: 'typingBounce 1s ease-in-out infinite',
          }} />
        )}
      </div>
    </div>
  );
}

function renderContent(text) {
  // Simple markdown-like rendering
  const lines = text.split('\n');
  const elements = [];
  let inCodeBlock = false;
  let codeContent = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} style={{ margin: '8px 0' }}>
            <code>{codeContent.join('\n')}</code>
          </pre>
        );
        codeContent = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    if (!line.trim()) {
      elements.push(<br key={`br-${i}`} />);
      continue;
    }

    // Bold
    let processed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Inline code
    processed = processed.replace(/`(.*?)`/g, '<code>$1</code>');
    // Risk emojis for tier mentions
    processed = processed.replace(/🔴\s*(critical)/gi, '🔴 <span style="color: var(--color-critical)">$1</span>');
    processed = processed.replace(/🟠\s*(warning)/gi, '🟠 <span style="color: var(--color-warning)">$1</span>');
    processed = processed.replace(/🟡\s*(watch)/gi, '🟡 <span style="color: var(--color-watch)">$1</span>');
    processed = processed.replace(/🟢\s*(healthy)/gi, '🟢 <span style="color: var(--color-healthy)">$1</span>');

    // Headers
    if (line.startsWith('### ')) {
      elements.push(<h4 key={i} style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, margin: '8px 0 4px' }}>{line.slice(4)}</h4>);
    } else if (line.startsWith('## ')) {
      elements.push(<h3 key={i} style={{ fontSize: 'var(--font-size-base)', fontWeight: 600, margin: '10px 0 4px' }}>{line.slice(3)}</h3>);
    } else if (line.startsWith('- ') || line.startsWith('• ')) {
      elements.push(
        <div key={i} style={{ paddingLeft: '16px', position: 'relative', marginBottom: '2px' }}>
          <span style={{ position: 'absolute', left: '4px' }}>•</span>
          <span dangerouslySetInnerHTML={{ __html: processed.slice(2) }} />
        </div>
      );
    } else if (/^\d+\.\s/.test(line)) {
      elements.push(
        <div key={i} style={{ paddingLeft: '20px', marginBottom: '2px' }}>
          <span dangerouslySetInnerHTML={{ __html: processed }} />
        </div>
      );
    } else {
      elements.push(<p key={i} dangerouslySetInnerHTML={{ __html: processed }} />);
    }
  }

  return <>{elements}</>;
}
