import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import * as endpoints from "../api/endpoints";
import { useAuth } from "../context/AuthContext.jsx";
import { PageHeader, SectionTitle } from "./DashboardPage.jsx";
import {
  PlasticPill,
  SuitabilityPill,
  RiskPill,
  PriorityPill,
  MaterialFlowBar,
  OutputBreakdownBar,
  SkeletonBlock,
  EmptyState,
} from "../components/Widgets.jsx";

export default function BatchDetailPage() {
  const { batchId } = useParams();
  const { hasPermission } = useAuth();
  const [batch, setBatch] = useState(null);
  const [composition, setComposition] = useState(null);
  const [detectionRuns, setDetectionRuns] = useState([]);
  const [report, setReport] = useState(null);
  const [loadingAction, setLoadingAction] = useState("");
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

  const refreshAll = async () => {
    const [b, c, runs, reports] = await Promise.all([
      endpoints.getBatch(batchId),
      endpoints.getBatchComposition(batchId).catch(() => ({ data: [] })),
      endpoints.listDetectionRuns(batchId).catch(() => ({ data: [] })),
      endpoints.getReportsForBatch(batchId).catch(() => ({ data: [] })),
    ]);
    setBatch(b.data);
    setComposition(c.data);
    setDetectionRuns(runs.data);
    if (reports.data.length > 0) setReport(reports.data[0]);
  };

  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]);

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setLoadingAction("upload");
    try {
      const uploadRes = await endpoints.uploadImage(batchId, file);
      setLoadingAction("detect");
      await endpoints.runDetection({ batch_id: parseInt(batchId, 10), image_path: uploadRes.data.image_path });
      await refreshAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Upload or detection failed.");
    } finally {
      setLoadingAction("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleGenerateReport = async () => {
    setError("");
    setLoadingAction("report");
    try {
      const res = await endpoints.generateReport({ batch_id: parseInt(batchId, 10) });
      setReport(res.data);
      const b = await endpoints.getBatch(batchId);
      setBatch(b.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Report generation failed.");
    } finally {
      setLoadingAction("");
    }
  };

  if (!batch) return <div style={{ padding: 32 }}><SkeletonBlock height={300} /></div>;

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1320 }}>
      <PageHeader
        title={batch.batch_code}
        subtitle={batch.source_description || "No source description provided."}
        action={
          hasPermission("trigger_detection") && (
            <div style={{ display: "flex", gap: 10 }}>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/bmp"
                style={{ display: "none" }}
                onChange={handleFileSelected}
              />
              <button className="btn" onClick={() => fileInputRef.current?.click()} disabled={!!loadingAction}>
                {loadingAction === "upload" ? "Uploading…" : loadingAction === "detect" ? "Detecting…" : "📷 Scan Image"}
              </button>
              <button
                className="btn btn-primary"
                onClick={handleGenerateReport}
                disabled={!!loadingAction || !composition?.length}
              >
                {loadingAction === "report" ? "Generating…" : "Generate Prediction Report"}
              </button>
            </div>
          )
        }
      />

      {error && (
        <div className="card" style={{ padding: 14, marginBottom: 20, borderColor: "var(--accent-hazard)", color: "var(--accent-hazard-bright)" }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
        <div className="card" style={{ padding: "16px 20px", flex: 1 }}>
          <div className="label-eyebrow">Status</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>{batch.status}</div>
        </div>
        <div className="card" style={{ padding: "16px 20px", flex: 1 }}>
          <div className="label-eyebrow">Total Weight</div>
          <div className="mono" style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>
            {batch.total_weight_tons != null ? `${batch.total_weight_tons.toFixed(3)} t` : "Awaiting scan"}
          </div>
        </div>
        <div className="card" style={{ padding: "16px 20px", flex: 1 }}>
          <div className="label-eyebrow">Detection Runs</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>{detectionRuns.length}</div>
        </div>
      </div>

      {/* Composition */}
      <div className="card" style={{ padding: 22, marginBottom: 20 }}>
        <SectionTitle>Detected Plastic Composition</SectionTitle>
        {(!composition || composition.length === 0) ? (
          <div style={{ marginTop: 14 }}>
            <EmptyState
              title="No scans yet"
              body='Click "Scan Image" above to run the AI plastic detector (computer vision) on a waste image and identify the polymer composition.'
            />
          </div>
        ) : (
          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 10 }}>
            {composition
              .sort((a, b) => b.weight_tons - a.weight_tons)
              .map((c) => (
                <div key={c.plastic_type} style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div style={{ width: 110 }}>
                    <PlasticPill type={c.plastic_type} />
                  </div>
                  <div className="mono" style={{ width: 90, fontSize: 13.5 }}>
                    {c.weight_tons.toFixed(3)} t
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--text-tertiary)", width: 90 }}>{c.item_count} items</div>
                  <div style={{ fontSize: 12.5, color: "var(--text-tertiary)" }}>
                    Avg confidence <span className="mono">{(c.avg_confidence * 100).toFixed(1)}%</span>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Prediction Report */}
      {report && <PredictionReportView report={report} />}
    </div>
  );
}

function PredictionReportView({ report }) {
  return (
    <>
      <div className="card" style={{ padding: 22, marginBottom: 20 }}>
        <SectionTitle>Executive Summary</SectionTitle>
        <p style={{ fontSize: 14.5, lineHeight: 1.65, color: "var(--text-primary)", marginTop: 12 }}>
          {report.executive_summary}
        </p>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
        <div className="card" style={{ padding: 22, flex: 1 }}>
          <SectionTitle>Feedstock Suitability</SectionTitle>
          <div style={{ marginTop: 16 }}>
            <MaterialFlowBar suitableTons={report.suitable_feedstock_tons} rejectedTons={report.rejected_tons} />
          </div>
          <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 10 }}>
            {report.suitability_lines.map((line, i) => (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: 13 }}>
                <PlasticPill type={line.plastic_type} />
                <SuitabilityPill value={line.suitability} />
                <span style={{ color: "var(--text-tertiary)", flex: 1 }}>{line.reason}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 22, flex: 1 }}>
          <SectionTitle>Predicted Pyrolysis Output</SectionTitle>
          <div style={{ marginTop: 16 }}>
            <OutputBreakdownBar oil={report.total_oil_tons} gas={report.total_gas_tons} char={report.total_char_tons} wax={report.total_wax_tons} />
          </div>
          <div style={{ marginTop: 16, fontSize: 13 }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-secondary)" }}>Overall oil yield</span>
              <span className="mono" style={{ fontWeight: 600 }}>{report.overall_oil_yield_pct}%</span>
            </div>
            {report.yield_lines.map((y, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                <span style={{ color: "var(--text-secondary)" }}>
                  <PlasticPill type={y.plastic_type} /> {y.input_tons.toFixed(2)}t in
                </span>
                <span className="mono">{y.oil_tons.toFixed(3)}t oil</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 22, marginBottom: 20 }}>
        <SectionTitle>Revenue Forecast</SectionTitle>
        <table style={{ width: "100%", marginTop: 14, fontSize: 13.5, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--text-tertiary)", fontSize: 11.5, textTransform: "uppercase" }}>
              <th style={{ padding: "6px 0" }}>Product</th>
              <th style={{ padding: "6px 0" }}>Quantity</th>
              <th style={{ padding: "6px 0" }}>Price / Ton</th>
              <th style={{ padding: "6px 0", textAlign: "right" }}>Revenue</th>
            </tr>
          </thead>
          <tbody>
            {report.revenue_lines.map((r, i) => (
              <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                <td style={{ padding: "9px 0" }}>{r.product}</td>
                <td className="mono" style={{ padding: "9px 0" }}>{r.quantity_tons.toFixed(3)} t</td>
                <td className="mono" style={{ padding: "9px 0" }}>${r.price_usd_per_ton.toFixed(2)}</td>
                <td className="mono" style={{ padding: "9px 0", textAlign: "right", fontWeight: 600 }}>
                  ${r.revenue_usd.toLocaleString()}
                </td>
              </tr>
            ))}
            <tr style={{ borderTop: "2px solid var(--border-strong)" }}>
              <td colSpan={3} style={{ padding: "10px 0", fontWeight: 700 }}>
                Total Revenue
              </td>
              <td className="mono" style={{ padding: "10px 0", textAlign: "right", fontWeight: 700, color: "var(--accent-oil)", fontSize: 16 }}>
                ${report.total_revenue_usd.toLocaleString()}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
        <div className="card" style={{ padding: 22, flex: 1 }}>
          <SectionTitle>Production Risks</SectionTitle>
          <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
            {report.risks.length === 0 ? (
              <span style={{ fontSize: 13.5, color: "var(--text-tertiary)" }}>No risks flagged for this batch.</span>
            ) : (
              report.risks.map((r, i) => (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <RiskPill severity={r.severity} />
                  <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1 }}>{r.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card" style={{ padding: 22, flex: 1 }}>
          <SectionTitle>Recommended Actions</SectionTitle>
          <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
            {report.recommendations.map((r, i) => (
              <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <PriorityPill priority={r.priority} />
                <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1 }}>{r.action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {report.assumptions.length > 0 && (
        <div className="card" style={{ padding: 22, marginBottom: 20 }}>
          <SectionTitle>Assumptions &amp; Confidence</SectionTitle>
          <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
            {report.assumptions.map((a, i) => (
              <div key={i} style={{ fontSize: 13 }}>
                <span style={{ fontWeight: 600 }}>{a.field}:</span>{" "}
                <span style={{ color: "var(--text-secondary)" }}>{a.assumption}</span>{" "}
                <span className="mono pill pill-neutral" style={{ marginLeft: 6 }}>
                  {a.confidence_pct}% confidence
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
