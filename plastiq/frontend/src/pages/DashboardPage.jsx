import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import * as endpoints from "../api/endpoints";
import { KpiCard, PlasticPill, SkeletonBlock, EmptyState } from "../components/Widgets.jsx";

export default function DashboardPage() {
  const { facility } = useOutletContext() || {};
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    endpoints
      .getDashboard(facility?.id)
      .then((res) => setData(res.data))
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load dashboard."))
      .finally(() => setLoading(false));
  }, [facility?.id]);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1320 }}>
      <PageHeader
        title="Operations Dashboard"
        subtitle="Real-time view of feedstock quality, pyrolysis yield, and revenue across recent batches."
      />

      {loading && (
        <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
          {[1, 2, 3, 4].map((i) => (
            <SkeletonBlock key={i} height={92} />
          ))}
        </div>
      )}

      {error && (
        <div className="card" style={{ padding: 16, borderColor: "var(--accent-hazard)", color: "var(--accent-hazard-bright)" }}>
          {error}
        </div>
      )}

      {data && !loading && data.kpis.batches_processed === 0 && (
        <EmptyState
          title="No prediction reports yet"
          body="Once a waste batch has been scanned and a prediction report generated, your KPIs, yield trends, and revenue forecasts will appear here."
        />
      )}

      {data && !loading && data.kpis.batches_processed > 0 && (
        <>
          <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
            <KpiCard
              label="Suitable Feedstock"
              value={data.kpis.total_suitable_feedstock_tons}
              unit="t"
              accent="var(--accent-good-bright)"
              sub={`${data.kpis.feedstock_utilization_pct}% of scanned waste`}
            />
            <KpiCard
              label="Oil Produced"
              value={data.kpis.total_oil_produced_tons}
              unit="t"
              accent="var(--accent-oil)"
              sub={`${data.kpis.overall_oil_yield_pct}% overall yield`}
            />
            <KpiCard
              label="Revenue Forecast"
              value={`$${data.kpis.total_revenue_usd.toLocaleString()}`}
              sub={`Net profit ≈ $${data.kpis.estimated_net_profit_usd.toLocaleString()}`}
            />
            <KpiCard
              label="Profit Margin"
              value={`${data.kpis.estimated_profit_margin_pct}%`}
              accent={data.kpis.estimated_profit_margin_pct < 15 ? "var(--accent-warn)" : "var(--accent-good-bright)"}
              sub={`Cost est. $${data.kpis.estimated_total_cost_usd.toLocaleString()}`}
            />
          </div>

          <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
            <KpiCard
              label="Avg PVC Contamination"
              value={`${data.kpis.avg_pvc_contamination_pct}%`}
              accent={data.kpis.avg_pvc_contamination_pct >= 5 ? "var(--accent-hazard-bright)" : "var(--accent-good-bright)"}
            />
            <KpiCard
              label="Critical Risks Open"
              value={data.kpis.open_critical_risks}
              accent={data.kpis.open_critical_risks > 0 ? "var(--accent-hazard-bright)" : "var(--text-primary)"}
            />
            <KpiCard label="Warning Risks Open" value={data.kpis.open_warning_risks} accent="var(--accent-warn)" />
            <KpiCard label="Batches Processed" value={data.kpis.batches_processed} sub={data.kpis.period_label} />
          </div>

          <div style={{ display: "flex", gap: 16, marginBottom: 20, alignItems: "stretch" }}>
            <div className="card" style={{ padding: 20, flex: 2, minWidth: 0 }}>
              <SectionTitle>Oil Yield Trend</SectionTitle>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={data.oil_yield_trend}>
                  <CartesianGrid stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" stroke="var(--text-tertiary)" fontSize={12} />
                  <YAxis stroke="var(--text-tertiary)" fontSize={12} unit=" t" />
                  <Tooltip
                    contentStyle={{ background: "var(--bg-surface-2)", border: "1px solid var(--border-strong)", borderRadius: 6 }}
                    labelStyle={{ color: "var(--text-secondary)" }}
                  />
                  <Line type="monotone" dataKey="value" stroke="var(--accent-oil)" strokeWidth={2} dot={{ r: 3 }} name="Oil (t)" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="card" style={{ padding: 20, flex: 1, minWidth: 280 }}>
              <SectionTitle>Plastic Composition</SectionTitle>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
                {data.plastic_breakdown.map((b) => (
                  <div key={b.plastic_type} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <PlasticPill type={b.plastic_type} />
                    <div style={{ flex: 1, height: 6, background: "var(--bg-surface-2)", borderRadius: 3, overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${b.pct_of_total}%`,
                          height: "100%",
                          background: "var(--accent-oil)",
                        }}
                      />
                    </div>
                    <span className="mono" style={{ fontSize: 12, color: "var(--text-secondary)", width: 64, textAlign: "right" }}>
                      {b.total_weight_tons.toFixed(2)} t
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card" style={{ padding: 20 }}>
            <SectionTitle>Revenue Trend</SectionTitle>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data.revenue_trend}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="label" stroke="var(--text-tertiary)" fontSize={12} />
                <YAxis stroke="var(--text-tertiary)" fontSize={12} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  contentStyle={{ background: "var(--bg-surface-2)", border: "1px solid var(--border-strong)", borderRadius: 6 }}
                  labelStyle={{ color: "var(--text-secondary)" }}
                  formatter={(v) => [`$${v.toLocaleString()}`, "Revenue"]}
                />
                <Line type="monotone" dataKey="value" stroke="var(--accent-good-bright)" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 26 }}>
      <div>
        <h1 style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 28, margin: 0, color: "var(--text-primary)" }}>
          {title}
        </h1>
        {subtitle && <p style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 6, maxWidth: 600 }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function SectionTitle({ children }) {
  return (
    <div
      style={{
        fontFamily: "var(--font-display)",
        fontWeight: 600,
        fontSize: 15,
        letterSpacing: "0.01em",
        color: "var(--text-primary)",
        textTransform: "uppercase",
      }}
    >
      {children}
    </div>
  );
}
