import { useEffect, useState } from "react";
import * as endpoints from "../api/endpoints";
import { useAuth } from "../context/AuthContext.jsx";
import { PageHeader } from "./DashboardPage.jsx";
import { EmptyState, SkeletonBlock } from "../components/Widgets.jsx";

export default function FacilitiesPage() {
  const { hasPermission } = useAuth();
  const [facilities, setFacilities] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const refresh = () => endpoints.listFacilities().then((res) => setFacilities(res.data));

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100 }}>
      <PageHeader
        title="Facilities"
        subtitle="Landfills, recycling centers, municipal waste facilities, and plastic-to-fuel plants registered in PlastiQ."
        action={
          hasPermission("configure_facilities") && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              + New Facility
            </button>
          )
        }
      />

      {!facilities && <SkeletonBlock height={160} />}

      {facilities && facilities.length === 0 && (
        <EmptyState
          title="No facilities registered"
          body="Register your first facility to start scanning waste, predicting pyrolysis yield, and forecasting revenue."
        />
      )}

      {facilities && facilities.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {facilities.map((f) => (
            <div key={f.id} className="card" style={{ padding: "18px 22px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 16, fontWeight: 600 }}>{f.name}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 3 }}>{f.location}</div>
              </div>
              <span className="pill pill-neutral">{(f.facility_type || "").replaceAll("_", " ")}</span>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateFacilityModal
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

function CreateFacilityModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [facilityType, setFacilityType] = useState("pyrolysis_plant");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await endpoints.createFacility({ name, location, facility_type: facilityType });
      onCreated();
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create facility.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={onClose}
    >
      <form onSubmit={handleSubmit} onClick={(e) => e.stopPropagation()} className="card" style={{ padding: 26, width: 420 }}>
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: 19, margin: "0 0 16px" }}>New Facility</h3>

        <Field label="Name">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Kumasi Pyrolysis Plant" required />
        </Field>
        <Field label="Location">
          <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Kumasi, Ashanti, Ghana" />
        </Field>
        <Field label="Facility Type">
          <select value={facilityType} onChange={(e) => setFacilityType(e.target.value)}>
            <option value="pyrolysis_plant">Pyrolysis / Plastic-to-Fuel Plant</option>
            <option value="recycling_center">Recycling Center</option>
            <option value="landfill">Landfill</option>
            <option value="municipal">Municipal Waste Facility</option>
          </select>
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
            {submitting ? "Creating…" : "Create Facility"}
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
