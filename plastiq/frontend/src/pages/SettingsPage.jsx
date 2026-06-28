import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import * as endpoints from "../api/endpoints";
import { PageHeader, SectionTitle } from "./DashboardPage.jsx";
import { SkeletonBlock, EmptyState } from "../components/Widgets.jsx";

const FIELD_GROUPS = [
  {
    title: "Pricing (USD per ton)",
    fields: [
      { key: "pyrolysis_oil_usd_per_ton", label: "Pyrolysis Oil" },
      { key: "carbon_black_usd_per_ton", label: "Carbon Black" },
      { key: "wax_usd_per_ton", label: "Wax Residue" },
      { key: "pyrolysis_gas_usd_per_ton", label: "Pyrolysis Gas" },
    ],
  },
  {
    title: "Cost & Profitability",
    fields: [
      { key: "processing_cost_usd_per_ton", label: "Processing Cost / Ton" },
      { key: "target_profit_margin_pct", label: "Target Profit Margin %" },
    ],
  },
  {
    title: "Risk Thresholds",
    fields: [
      { key: "pvc_contamination_warning_pct", label: "PVC Contamination — Warning %" },
      { key: "pvc_contamination_critical_pct", label: "PVC Contamination — Critical %" },
      { key: "machine_utilization_warning_pct", label: "Reactor Utilization — Warning %" },
      { key: "safety_stock_feedstock_tons", label: "Safety Stock — Feedstock (tons)" },
      { key: "low_confidence_threshold", label: "Low-Confidence Detection Threshold" },
    ],
  },
];

export default function SettingsPage() {
  const { facility } = useOutletContext() || {};
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!facility?.id) return;
    endpoints.getAISettings(facility.id).then((res) => setSettings(res.data));
  }, [facility?.id]);

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = {};
      for (const group of FIELD_GROUPS) {
        for (const f of group.fields) {
          payload[f.key] = parseFloat(settings[f.key]);
        }
      }
      const res = await endpoints.updateAISettings(facility.id, payload);
      setSettings(res.data);
      setSaved(true);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  if (!facility) {
    return (
      <div style={{ padding: "28px 32px" }}>
        <PageHeader title="AI Settings" />
        <EmptyState title="No facility selected" body="Register a facility first to configure pricing, cost, and risk thresholds." />
      </div>
    );
  }

  return (
    <div style={{ padding: "28px 32px", maxWidth: 760 }}>
      <PageHeader
        title="AI Settings"
        subtitle={`Pricing, cost assumptions, and risk thresholds used by the prediction engine for ${facility.name}.`}
      />

      {!settings && <SkeletonBlock height={400} />}

      {settings && (
        <>
          {FIELD_GROUPS.map((group) => (
            <div key={group.title} className="card" style={{ padding: 22, marginBottom: 18 }}>
              <SectionTitle>{group.title}</SectionTitle>
              <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {group.fields.map((f) => (
                  <div key={f.key}>
                    <label style={{ display: "block", fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 6 }}>
                      {f.label}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={settings[f.key] ?? ""}
                      onChange={(e) => handleChange(f.key, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}

          {error && (
            <div className="card" style={{ padding: 14, marginBottom: 16, borderColor: "var(--accent-hazard)", color: "var(--accent-hazard-bright)" }}>
              {error}
            </div>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save Settings"}
            </button>
            {saved && <span style={{ fontSize: 13, color: "var(--accent-good-bright)" }}>✓ Saved</span>}
          </div>
        </>
      )}
    </div>
  );
}
