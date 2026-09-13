import React from 'react';

export default function Sidebar({ activeView, onViewChange }) {
  const navItems = [
    { id: 'chat', label: 'AI Assistant', icon: '💬' },
    { id: 'dashboard', label: 'Fleet Dashboard', icon: '📊' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">⚡</div>
          <div>
            <h1>FleetPulse</h1>
            <span>Predictive Device Intelligence</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
          <div
            key={item.id}
            className={`sidebar-nav-item ${activeView === item.id ? 'active' : ''}`}
            onClick={() => onViewChange(item.id)}
          >
            <span className="icon">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ marginBottom: '4px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>
          FleetPulse v0.1.0
        </div>
        <div>ML + RAG + Agentic AI</div>
      </div>
    </aside>
  );
}
