import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import FleetDashboard from './components/FleetDashboard';

export default function App() {
  const [activeView, setActiveView] = useState('chat');

  return (
    <div className="app-layout">
      <Sidebar activeView={activeView} onViewChange={setActiveView} />
      <div className="main-content">
        {activeView === 'chat' ? <ChatPanel /> : <FleetDashboard />}
      </div>
    </div>
  );
}
