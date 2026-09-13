import React, { useState } from 'react';

const PRIORITY_COLORS = {
  P1: { bg: 'var(--color-critical-bg)', color: 'var(--color-critical)', label: 'P1 - Urgent' },
  P2: { bg: 'var(--color-warning-bg)', color: 'var(--color-warning)', label: 'P2 - High' },
  P3: { bg: 'var(--color-watch-bg)', color: 'var(--color-watch)', label: 'P3 - Medium' },
  P4: { bg: 'var(--color-healthy-bg)', color: 'var(--color-healthy)', label: 'P4 - Low' },
};

export default function TicketPreview({ ticket }) {
  const [copied, setCopied] = useState(false);

  if (!ticket) return null;

  const {
    ticket_id,
    created_at,
    status = 'Draft',
    priority = 'P2',
    type = 'Preventive Maintenance',
    device = {},
    prediction = {},
    repair_details = {},
    actions = [],
    estimated_downtime_hours,
    estimated_cost_usd,
    formatted_summary,
  } = ticket;

  const priorityStyle = PRIORITY_COLORS[priority] || PRIORITY_COLORS.P3;

  const handleCopy = () => {
    const textToCopy = formatted_summary || JSON.stringify(ticket, null, 2);
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card" style={{
      marginTop: 'var(--space-sm)',
      background: 'linear-gradient(180deg, rgba(21, 29, 51, 0.9) 0%, rgba(15, 22, 41, 0.95) 100%)',
      border: '1px solid rgba(59, 130, 246, 0.25)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--shadow-md)',
    }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)', borderBottom: '1px solid var(--color-border)', paddingBottom: 'var(--space-xs)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <span style={{ fontSize: '1.2rem' }}>🎫</span>
          <div>
            <div style={{ fontWeight: 700, color: 'var(--color-text-primary)', fontSize: 'var(--font-size-base)' }}>
              Remediation Ticket: <span style={{ fontFamily: 'monospace', color: 'var(--color-accent-blue)' }}>{ticket_id}</span>
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              {type} • Generated {created_at ? new Date(created_at).toLocaleDateString() : 'Just now'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
          <span className="badge" style={{ background: priorityStyle.bg, color: priorityStyle.color, fontWeight: 700 }}>
            {priorityStyle.label}
          </span>
          <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.08)', color: 'var(--color-text-secondary)' }}>
            {status}
          </span>
        </div>
      </div>

      {/* Details Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: 'var(--space-sm)',
        marginBottom: 'var(--space-md)',
      }}>
        <div style={{ background: 'var(--color-bg-primary)', padding: 'var(--space-xs) var(--space-sm)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Device ID</div>
          <div style={{ fontWeight: 600, fontFamily: 'monospace', fontSize: 'var(--font-size-sm)' }}>{device.device_id || 'N/A'}</div>
        </div>
        <div style={{ background: 'var(--color-bg-primary)', padding: 'var(--space-xs) var(--space-sm)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Model</div>
          <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>{device.device_model || 'N/A'}</div>
        </div>
        <div style={{ background: 'var(--color-bg-primary)', padding: 'var(--space-xs) var(--space-sm)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Target Fleet</div>
          <div style={{ fontWeight: 600, fontSize: 'var(--font-size-sm)' }}>{device.fleet || 'All Fleets'}</div>
        </div>
        <div style={{ background: 'var(--color-bg-primary)', padding: 'var(--space-xs) var(--space-sm)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Failing Component</div>
          <div style={{ fontWeight: 600, color: 'var(--color-critical)', fontSize: 'var(--font-size-sm)' }}>
            {(device.failing_component || 'Battery').replace(/_/g, ' ').toUpperCase()}
          </div>
        </div>
      </div>

      {/* Issue Summary */}
      {prediction.issue_summary && (
        <div style={{ marginBottom: 'var(--space-sm)', padding: 'var(--space-xs) var(--space-sm)', background: 'rgba(239, 68, 68, 0.08)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 600 }}>DIAGNOSTIC FINDING</div>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>{prediction.issue_summary}</div>
          {prediction.remaining_useful_life_days && (
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-warning)', marginTop: '2px' }}>
              Remaining Useful Life: ~{prediction.remaining_useful_life_days} days
            </div>
          )}
        </div>
      )}

      {/* Part details */}
      {repair_details.part_number && (
        <div style={{ marginBottom: 'var(--space-sm)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', background: 'var(--color-bg-tertiary)', padding: 'var(--space-xs) var(--space-sm)', borderRadius: 'var(--radius-sm)' }}>
          <strong>Required Part:</strong> {repair_details.part_number} | <strong>Vendor:</strong> {repair_details.supplier || 'OEM'} | <strong>Est. Cost:</strong> ${repair_details.estimated_cost_usd || estimated_cost_usd || 0}
        </div>
      )}

      {/* Recommended Action Checklist */}
      {actions && actions.length > 0 && (
        <div style={{ marginBottom: 'var(--space-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '4px' }}>
            REMEDIATION WORKFLOW:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {actions.map((act, i) => (
              <div key={i} style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--color-accent-blue)' }}>▹</span> {act}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-sm)', marginTop: 'var(--space-xs)' }}>
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
          Est. Downtime: {estimated_downtime_hours || 1.5} hrs
        </div>
        <button
          className="btn btn-secondary"
          onClick={handleCopy}
          style={{ fontSize: 'var(--font-size-xs)', padding: '4px 12px' }}
        >
          {copied ? '✓ Copied to Clipboard' : '📋 Copy Ticket'}
        </button>
      </div>
    </div>
  );
}
