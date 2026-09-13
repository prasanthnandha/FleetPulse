import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { useFleetData } from '../hooks/useFleetData';
import DeviceCard from './DeviceCard';

const FLEET_OPTIONS = ['All Fleets', 'Sales', 'Engineering', 'Executive', 'Support', 'Marketing', 'Operations'];

const PIE_COLORS = {
  critical: '#ef4444',
  warning: '#f97316',
  watch: '#f59e0b',
  healthy: '#10b981',
};

export default function FleetDashboard() {
  const { overview, devices, trends, isLoading, selectedFleet, loadAll } = useFleetData();

  const handleFleetChange = (e) => {
    const fleet = e.target.value === 'All Fleets' ? null : e.target.value;
    loadAll(fleet);
  };

  if (isLoading && !overview) {
    return (
      <div className="main-content">
        <div className="dashboard-header">
          <h2>📊 Fleet Dashboard</h2>
        </div>
        <div className="dashboard" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="typing-indicator">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
          </div>
        </div>
      </div>
    );
  }

  const riskDist = overview?.risk_distribution || {};
  const pieData = Object.entries(riskDist)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  const trendData = trends?.trend_data?.map(t => ({
    ...t,
    date: t.date.slice(5), // MM-DD
  })) || [];

  return (
    <div className="main-content">
      {/* Header */}
      <div className="dashboard-header">
        <h2>📊 Fleet Dashboard</h2>
        <select
          value={selectedFleet || 'All Fleets'}
          onChange={handleFleetChange}
          style={{
            background: 'var(--color-bg-tertiary)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-primary)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--font-size-xs)',
            cursor: 'pointer',
          }}
        >
          {FLEET_OPTIONS.map(f => <option key={f} value={f}>{f}</option>)}
        </select>
      </div>

      <div className="dashboard">
        {/* Stat Cards */}
        <div className="dashboard-grid dashboard-stats animate-slide-up">
          <div className="glass-card stat-card">
            <div className="stat-card-label">Total Devices</div>
            <div className="stat-card-value">{overview?.total_devices || 0}</div>
            <div className="stat-card-trend" style={{ color: 'var(--color-text-muted)' }}>
              {selectedFleet ? `${selectedFleet} fleet` : 'All fleets'}
            </div>
          </div>

          <div className="glass-card stat-card">
            <div className="stat-card-label">Avg Risk Score</div>
            <div className="stat-card-value" style={{
              color: overview?.avg_risk_score > 60 ? 'var(--color-warning)' :
                overview?.avg_risk_score > 40 ? 'var(--color-watch)' : 'var(--color-healthy)'
            }}>
              {overview?.avg_risk_score?.toFixed(1) || '—'}
            </div>
            <div className="stat-card-trend">
              <span>/100</span>
            </div>
          </div>

          <div className="glass-card stat-card">
            <div className="stat-card-label">Need Attention</div>
            <div className="stat-card-value" style={{
              color: overview?.devices_needing_attention > 0 ? 'var(--color-critical)' : 'var(--color-healthy)'
            }}>
              {overview?.devices_needing_attention || 0}
            </div>
            <div className="stat-card-trend up">
              Within 30 days
            </div>
          </div>

          <div className="glass-card stat-card">
            <div className="stat-card-label">Avg Battery Health</div>
            <div className="stat-card-value" style={{
              color: overview?.avg_battery_health > 70 ? 'var(--color-healthy)' :
                overview?.avg_battery_health > 50 ? 'var(--color-watch)' : 'var(--color-critical)'
            }}>
              {overview?.avg_battery_health?.toFixed(0) || '—'}%
            </div>
            <div className="stat-card-trend">
              Fleet average
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="dashboard-grid dashboard-charts">
          {/* Risk Trend Chart */}
          <div className="glass-card chart-card animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <div className="chart-card-title">Risk Score Trend (30 days)</div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fill: '#5a6478', fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#5a6478', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    background: '#151d33',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="avg_risk_score"
                  stroke="#3b82f6"
                  fill="url(#riskGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Risk Distribution Pie */}
          <div className="glass-card chart-card animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <div className="chart-card-title">Risk Distribution</div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 32 }}>
              <ResponsiveContainer width={180} height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={PIE_COLORS[entry.name] || '#5a6478'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#151d33',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Object.entries(riskDist).map(([tier, count]) => (
                  <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--font-size-xs)' }}>
                    <div className={`risk-dot ${tier}`} />
                    <span style={{ color: 'var(--color-text-secondary)', textTransform: 'capitalize' }}>{tier}</span>
                    <span style={{ fontWeight: 700, marginLeft: 4 }}>{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Device List */}
        <div className="dashboard-grid dashboard-devices">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--space-sm)',
          }}>
            <h3 style={{
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-text-secondary)',
            }}>
              Devices — Sorted by Risk
            </h3>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              {devices.length} devices
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            {devices.map((device) => (
              <DeviceCard key={device.device_id} device={device} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
