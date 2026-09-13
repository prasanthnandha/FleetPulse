import React from 'react';

export default function DeviceCard({ device, onClick }) {
  const {
    device_id,
    device_model,
    fleet_name,
    risk_tier,
    overall_risk_score,
    battery_health_score,
    compliance_score,
    remaining_useful_life_days,
    driving_factors,
  } = device;

  const riskColor = {
    healthy: 'var(--color-healthy)',
    watch: 'var(--color-watch)',
    warning: 'var(--color-warning)',
    critical: 'var(--color-critical)',
  }[risk_tier] || 'var(--color-text-muted)';

  return (
    <div className="glass-card device-card" onClick={() => onClick?.(device)}>
      {/* Risk dot */}
      <div className={`risk-dot ${risk_tier}`} />

      {/* Device info */}
      <div className="device-card-info">
        <div className="device-card-name">{device_model}</div>
        <div className="device-card-meta">
          {device_id} • {fleet_name}
          {driving_factors?.length > 0 && (
            <span style={{ color: riskColor, marginLeft: 8 }}>
              {driving_factors.filter(f => f !== 'nominal').slice(0, 2).join(', ')}
            </span>
          )}
        </div>
      </div>

      {/* Risk Score */}
      <div className="device-card-metric">
        <div className="device-card-metric-value" style={{ color: riskColor }}>
          {Math.round(overall_risk_score)}
        </div>
        <div className="device-card-metric-label">Risk</div>
      </div>

      {/* Battery Health */}
      <div className="device-card-metric">
        <div className="device-card-metric-value">
          {battery_health_score != null ? `${Math.round(battery_health_score)}%` : '—'}
        </div>
        <div className="device-card-metric-label">Battery</div>
      </div>

      {/* RUL */}
      <div className="device-card-metric">
        <div className="device-card-metric-value" style={{
          color: remaining_useful_life_days != null && remaining_useful_life_days < 30
            ? 'var(--color-warning)' : 'inherit'
        }}>
          {remaining_useful_life_days != null ? `${Math.round(remaining_useful_life_days)}d` : '—'}
        </div>
        <div className="device-card-metric-label">RUL</div>
      </div>
    </div>
  );
}
