import { useState, useRef, useCallback } from 'react';

const API_BASE = '/api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [activeToolCalls, setActiveToolCalls] = useState([]);
  const abortControllerRef = useRef(null);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;

    const userMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setActiveToolCalls([]);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      if (!response.ok) throw new Error(`API error: ${response.status}`);

      const data = await response.json();
      setSessionId(data.session_id);

      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        toolCalls: data.tool_calls || [],
        toolResults: data.tool_results || [],
        timestamp: data.timestamp,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        role: 'assistant',
        content: `I apologize, but I encountered an error: ${error.message}. Please try again.`,
        isError: true,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setActiveToolCalls([]);
    }
  }, [isLoading, sessionId]);

  const sendMessageStreaming = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;

    const userMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setActiveToolCalls([]);

    // Add a placeholder for the assistant message
    const placeholderId = Date.now();
    setMessages(prev => [...prev, {
      id: placeholderId,
      role: 'assistant',
      content: '',
      toolCalls: [],
      toolResults: [],
      isStreaming: true,
    }]);

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.session_id) {
                setSessionId(data.session_id);
              } else if (data.content !== undefined) {
                // Text chunk
                setMessages(prev => prev.map(m =>
                  m.id === placeholderId
                    ? { ...m, content: m.content + data.content }
                    : m
                ));
              } else if (data.tool) {
                if (data.arguments) {
                  // Tool call
                  setActiveToolCalls(prev => [...prev, { tool: data.tool, arguments: data.arguments }]);
                  setMessages(prev => prev.map(m =>
                    m.id === placeholderId
                      ? { ...m, toolCalls: [...m.toolCalls, { tool: data.tool, arguments: data.arguments }] }
                      : m
                  ));
                } else if (data.result) {
                  // Tool result
                  setMessages(prev => prev.map(m =>
                    m.id === placeholderId
                      ? { ...m, toolResults: [...m.toolResults, { tool: data.tool, result: data.result }] }
                      : m
                  ));
                }
              } else if (data.full_response !== undefined) {
                // Done
                setMessages(prev => prev.map(m =>
                  m.id === placeholderId
                    ? { ...m, isStreaming: false, content: data.full_response || m.content }
                    : m
                ));
              }
            } catch (e) {
              // Skip malformed events
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      setMessages(prev => prev.map(m =>
        m.id === placeholderId
          ? { ...m, content: `Error: ${error.message}`, isError: true, isStreaming: false }
          : m
      ));
    } finally {
      setIsLoading(false);
      setActiveToolCalls([]);
    }
  }, [isLoading, sessionId]);

  const clearChat = useCallback(async () => {
    if (sessionId) {
      try {
        await fetch(`${API_BASE}/chat/session/${sessionId}`, { method: 'DELETE' });
      } catch (e) { /* ignore */ }
    }
    setMessages([]);
    setSessionId(null);
    setActiveToolCalls([]);
  }, [sessionId]);

  return {
    messages,
    isLoading,
    sessionId,
    activeToolCalls,
    sendMessage,
    sendMessageStreaming,
    clearChat,
  };
}
