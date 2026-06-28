import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import * as endpoints from "../api/endpoints";
import { useAuth } from "../context/AuthContext.jsx";
import { PageHeader } from "./DashboardPage.jsx";
import { EmptyState, SkeletonBlock } from "../components/Widgets.jsx";

const STATUS_STYLES = {
  RECEIVED: { label: "Received", cls: "pill-neutral" },
  SCANNED: { label: "Scanned", cls: "pill-warn" },
  PROCESSED: { label: "Processed", cls: "pill-good" },
  REJECTED: { label: "Rejected", cls: "pill-hazard" },
};

export default function BatchesPage() {
  const { facility } = useOutletContext() || {};
  const { hasPermission } = useAuth();
  const [batches, setBatches] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const refresh = () => {
    endpoints.listBatches(facility?.id).then((res) => setBatches(res.data));
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facility?.id]);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1320 }}>
      <PageHeader
        title="Waste Batches"
        subtitle="Every intake of waste material — from a truck, landfill load, or conveyor session — with its scan and pyrolysis prediction status."
        action={
          hasPermission("trigger_detection") && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              + New Batch
            </button>
          )
        }
      />

      {!batches && <SkeletonBlock height={240} />}

      {batches && batches.length === 0 && (
        <EmptyState
          title="No waste batches yet"
          body="Create a batch to represent an intake of waste material, then upload images and run detection to identify the plastic composition."
          action={
            hasPermission("trigger_detection") && (
              <button className="btn btn-primary" onClick={() => setShowCreate(true)} style={{ marginTop: 8 }}>
                + New Batch
              </button>
            )
          }
        />
      )}

      {batches && batches.length > 0 && (
        <div className="card" style={{ overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
            <thead>
              <tr style={{ background: "var(--bg-surface-2)", textAlign: "left" }}>
                <Th>Batch Code</Th>
                <Th>Source</Th>
                <Th>Total Weight</Th>
                <Th>Status</Th>
                <Th>Received</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => {
                const status = STATUS_STYLES[b.status] || STATUS_STYLES.RECEIVED;
                return (
                  <tr key={b.id} style={{ borderTop: "1px solid var(--border)" }}>
                    <Td>
                      <span className="mono" style={{ fontWeight: 600 }}>
                        {b.batch_code}
                      </span>
                    </Td>
                    <Td style={{ color: "var(--text-secondary)" }}>{b.source_description || "—"}</Td>
                    <Td className="mono">{b.total_weight_tons != null ? `${b.total_weight_tons.toFixed(2)} t` : "Pending scan"}</Td>
                    <Td>
                      <span className={`pill ${status.cls}`}>{status.label}</span>
                    </Td>
                    <Td style={{ color: "var(--text-tertiary)" }}>{new Date(b.received_at).toLocaleString()}</Td>
                    <Td>
                      <Link to={`/batches/${b.id}`} className="btn" style={{ padding: "6px 12px", fontSize: 12.5 }}>
                        Open →
                      </Link>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateBatchModal
          facilityId={facility?.id}
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function Th({ children }) {
  return (
    <th style={{ padding: "11px 16px", fontSize: 11.5, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--text-tertiary)", fontWeight: 600 }}>
      {children}
    </th>
  );
}
function Td({ children, className, style }) {
  return (
    <td className={className} style={{ padding: "13px 16px", color: "var(--text-primary)", ...style }}>
      {children}
    </td>
  );
}

function CreateBatchModal({ facilityId, onClose, onCreated }) {
  const [batchCode, setBatchCode] = useState("");
  const [sourceDescription, setSourceDescription] = useState("");
  const [weight, setWeight] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!facilityId) {
      setError("No facility configured yet. Create a facility first.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await endpoints.createBatch({
        facility_id: facilityId,
        batch_code: batchCode,
        source_description: sourceDescription || null,
        total_weight_tons: weight ? parseFloat(weight) : null,
      });
      onCreated();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create batch.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{ padding: 26, width: 420 }}
      >
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 19, margin: "0 0 16px" }}>New Waste Batch</h3>

        <Field label="Batch Code">
          <input value={batchCode} onChange={(e) => setBatchCode(e.target.value)} placeholder="BATCH-0006" required />
        </Field>
        <Field label="Source Description (optional)">
          <input value={sourceDescription} onChange={(e) => setSourceDescription(e.target.value)} placeholder="Municipal collection route 4" />
        </Field>
        <Field label="Total Weight in Tons (optional — leave blank to derive from scan)">
          <input type="number" step="0.01" min="0" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="10.0" />
        </Field>

        {error && (
          <div style={{ background: "var(--accent-hazard-dim)", color: "var(--accent-hazard-bright)", fontSize: 13, padding: "9px 12px", borderRadius: 6, marginBottom: 14 }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
          <button type="button" className="btn" onClick={onClose} style={{ flex: 1 }}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting} style={{ flex: 1 }}>
            {submitting ? "Creating…" : "Create Batch"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: "block", fontSize: 12.5, color: "var(--text-secondary)", marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  );
}
