import React from 'react';

export default function PartInfo({ partData }) {
  if (!partData) return null;

  const {
    device_model,
    component,
    part_number,
    supplier,
    cost_usd,
    estimated_repair_time_hours,
    availability,
    warranty_months,
    confidence,
    procedure_summary,
    safety_warnings,
    tools_required,
    message,
    found,
  } = partData;

  if (found === false) {
    return (
      <div className="card" style={{ marginTop: 'var(--space-sm)', borderLeft: '3px solid var(--color-watch)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <span style={{ fontSize: '1.2rem' }}>⚠️</span>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--color-watch)' }}>Part Information Unavailable</div>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
              {message || 'No confident match found. Please escalate this inquiry to IT hardware engineering.'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: 'var(--space-sm)', borderLeft: '3px solid var(--color-accent-blue)' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-sm)' }}>
        <div>
          <div style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-accent-blue)', fontWeight: 600 }}>
            RAG Hardware Spec
          </div>
          <div style={{ fontSize: 'var(--font-size-base)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            {device_model} — {component ? component.replace(/_/g, ' ').toUpperCase() : 'Replacement Part'}
          </div>
        </div>
        {confidence !== undefined && (
          <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: 'var(--color-accent-blue)' }}>
            {(confidence * 100).toFixed(0)}% Match Confidence
          </span>
        )}
      </div>

      {/* Part Specifications Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: 'var(--space-sm)',
        background: 'var(--color-bg-tertiary)',
        padding: 'var(--space-sm) var(--space-md)',
        borderRadius: 'var(--radius-md)',
        marginBottom: 'var(--space-sm)',
      }}>
        <div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Part Number</div>
          <div style={{ fontWeight: 600, fontFamily: 'monospace', color: 'var(--color-text-primary)' }}>
            {part_number || 'N/A'}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Supplier</div>
          <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{supplier || 'OEM / Certified'}</div>
        </div>
        <div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Est. Cost</div>
          <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
            {cost_usd ? `$${cost_usd.toFixed(2)}` : 'Contact Vendor'}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Repair Window</div>
          <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
            {estimated_repair_time_hours ? `${estimated_repair_time_hours} hrs` : '1.5 hrs'}
          </div>
        </div>
        {availability && (
          <div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Availability</div>
            <div style={{ fontWeight: 600, color: availability === 'in_stock' ? 'var(--color-healthy)' : 'var(--color-watch)' }}>
              {availability.replace('_', ' ').toUpperCase()}
            </div>
          </div>
        )}
        {warranty_months && (
          <div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Warranty</div>
            <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{warranty_months} Mos</div>
          </div>
        )}
      </div>

      {/* Safety Warnings */}
      {safety_warnings && safety_warnings.length > 0 && (
        <div style={{ marginBottom: 'var(--space-sm)', padding: 'var(--space-xs) var(--space-sm)', background: 'var(--color-warning-bg)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--color-warning)', marginBottom: '2px' }}>
            Safety Advisories:
          </div>
          <ul style={{ margin: 0, paddingLeft: '16px', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
            {safety_warnings.map((warn, i) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Tools Required */}
      {tools_required && tools_required.length > 0 && (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
          <span style={{ color: 'var(--color-text-muted)' }}>Tools needed: </span>
          {tools_required.join(', ')}
        </div>
      )}

      {/* Procedure Summary */}
      {procedure_summary && (
        <div style={{ marginTop: 'var(--space-xs)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-xs)' }}>
          <span style={{ color: 'var(--color-text-muted)', fontWeight: 600 }}>Procedure: </span>
          {procedure_summary}
        </div>
      )}
    </div>
  );
}
