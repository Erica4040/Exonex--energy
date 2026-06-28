// Shared, reusable presentation components used across Dashboard/Batch pages.

export const PLASTIC_COLORS = {
  PET: "#7fb3d5",
  HDPE: "var(--accent-good-bright)",
  LDPE: "var(--accent-good-bright)",
  PP: "#54c4b7",
  PS: "var(--accent-warn)",
  PVC: "var(--accent-hazard-bright)",
  MIXED: "#a89bd1",
  OTHER: "var(--text-tertiary)",
};

export const SUITABILITY_LABELS = {
  HIGHLY_SUITABLE: { label: "Highly Suitable", cls: "pill-good" },
  MODERATE: { label: "Moderate", cls: "pill-warn" },
  POOR_HAZARDOUS: { label: "Poor / Hazardous", cls: "pill-hazard" },
  UNKNOWN: { label: "Unknown", cls: "pill-neutral" },
};

export function KpiCard({ label, value, unit, accent, sub }) {
  return (
    <div className="card" style={{ padding: "18px 20px", flex: 1, minWidth: 0 }}>
      <div className="label-eyebrow">{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 8 }}>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: 34,
            lineHeight: 1,
            color: accent || "var(--text-primary)",
          }}
        >
          {value}
        </span>
        {unit && <span style={{ fontSize: 14, color: "var(--text-tertiary)" }}>{unit}</span>}
      </div>
      {sub && <div style={{ fontSize: 12.5, color: "var(--text-secondary)", marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

export function PlasticPill({ type }) {
  const color = PLASTIC_COLORS[type] || "var(--text-tertiary)";
  return (
    <span
      className="pill"
      style={{
        background: "var(--bg-surface-2)",
        border: "1px solid var(--border-strong)",
        color: "var(--text-primary)",
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block" }} />
      {type}
    </span>
  );
}

export function SuitabilityPill({ value }) {
  const conf = SUITABILITY_LABELS[value] || SUITABILITY_LABELS.UNKNOWN;
  return <span className={`pill ${conf.cls}`}>{conf.label}</span>;
}

export function RiskPill({ severity }) {
  const map = {
    CRITICAL: { label: "Critical", cls: "pill-hazard" },
    WARNING: { label: "Warning", cls: "pill-warn" },
    INFO: { label: "Info", cls: "pill-neutral" },
  };
  const conf = map[severity] || map.INFO;
  return <span className={`pill ${conf.cls}`}>{conf.label}</span>;
}

export function PriorityPill({ priority }) {
  const map = {
    HIGH: { label: "High", cls: "pill-hazard" },
    MEDIUM: { label: "Medium", cls: "pill-warn" },
    LOW: { label: "Low", cls: "pill-good" },
  };
  const conf = map[priority] || map.LOW;
  return <span className={`pill ${conf.cls}`}>{conf.label}</span>;
}

/**
 * The signature element: a horizontal material-flow bar.
 * Shows total waste mass flowing into "suitable" vs "rejected" segments,
 * proportionally sized — a literal visualization of the sorting decision,
 * rather than a generic pie chart.
 */
export function MaterialFlowBar({ suitableTons, rejectedTons }) {
  const total = suitableTons + rejectedTons || 1;
  const suitablePct = (suitableTons / total) * 100;
  const rejectedPct = 100 - suitablePct;

  return (
    <div>
      <div style={{ display: "flex", height: 28, borderRadius: "var(--radius-md)", overflow: "hidden", border: "1px solid var(--border)" }}>
        <div
          style={{
            width: `${suitablePct}%`,
            background: "var(--accent-good)",
            transition: "width 0.4s ease",
          }}
          title={`Suitable: ${suitableTons.toFixed(2)} t`}
        />
        <div
          style={{
            width: `${rejectedPct}%`,
            background: "var(--accent-hazard-dim)",
            transition: "width 0.4s ease",
          }}
          title={`Rejected: ${rejectedTons.toFixed(2)} t`}
        />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12.5 }}>
        <span style={{ color: "var(--accent-good-bright)" }}>
          ● Suitable feedstock — <span className="mono">{suitableTons.toFixed(2)} t</span>
        </span>
        <span style={{ color: "var(--accent-hazard-bright)" }}>
          ● Rejected — <span className="mono">{rejectedTons.toFixed(2)} t</span>
        </span>
      </div>
    </div>
  );
}

/**
 * Stacked output bar for oil / gas / char / wax — the pyrolysis product split.
 */
export function OutputBreakdownBar({ oil, gas, char, wax }) {
  const total = oil + gas + char + wax || 1;
  const segments = [
    { key: "Oil", value: oil, color: "var(--accent-oil)" },
    { key: "Gas", value: gas, color: "var(--accent-gas)" },
    { key: "Carbon Black", value: char, color: "var(--accent-char)" },
    { key: "Wax", value: wax, color: "var(--accent-wax)" },
  ];

  return (
    <div>
      <div style={{ display: "flex", height: 28, borderRadius: "var(--radius-md)", overflow: "hidden", border: "1px solid var(--border)" }}>
        {segments.map((s) => (
          <div
            key={s.key}
            style={{ width: `${(s.value / total) * 100}%`, background: s.color, transition: "width 0.4s ease" }}
            title={`${s.key}: ${s.value.toFixed(3)} t`}
          />
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 14, marginTop: 8, fontSize: 12.5 }}>
        {segments.map((s) => (
          <span key={s.key} style={{ color: "var(--text-secondary)" }}>
            <span style={{ color: s.color }}>●</span> {s.key} — <span className="mono">{s.value.toFixed(3)} t</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export function EmptyState({ title, body, action }) {
  return (
    <div
      className="card"
      style={{
        padding: "48px 32px",
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
      }}
    >
      <div style={{ fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 600, color: "var(--text-primary)" }}>
        {title}
      </div>
      <div style={{ fontSize: 14, color: "var(--text-secondary)", maxWidth: 420 }}>{body}</div>
      {action}
    </div>
  );
}

export function SkeletonBlock({ height = 80 }) {
  return <div className="skeleton" style={{ height, width: "100%" }} />;
}
