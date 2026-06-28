import { NavLink, Outlet } from "react-router-dom";
import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import * as endpoints from "../api/endpoints";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: GaugeIcon, permission: "view_dashboards" },
  { to: "/batches", label: "Waste Batches", icon: LayersIcon, permission: "view_detections" },
  { to: "/facilities", label: "Facilities", icon: BuildingIcon, permission: null },
  { to: "/settings", label: "AI Settings", icon: SlidersIcon, permission: "configure_ai_settings" },
];

export default function AppLayout() {
  const { user, doLogout, hasPermission } = useAuth();
  const [facility, setFacility] = useState(null);

  useEffect(() => {
    endpoints
      .listFacilities()
      .then((res) => {
        if (res.data.length > 0) setFacility(res.data[0]);
      })
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 248,
          flexShrink: 0,
          background: "var(--bg-surface)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          position: "sticky",
          top: 0,
          height: "100vh",
        }}
      >
        <div style={{ padding: "22px 20px 18px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <LogoMark />
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: 21,
                letterSpacing: "0.01em",
                color: "var(--text-primary)",
              }}
            >
              PLASTI<span style={{ color: "var(--accent-oil)" }}>Q</span>
            </div>
          </div>
          <div className="label-eyebrow" style={{ marginTop: 6, marginLeft: 2 }}>
            Pyrolysis Yield Intelligence
          </div>
        </div>

        {facility && (
          <div
            style={{
              padding: "14px 20px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <div className="label-eyebrow">Active Facility</div>
            <div style={{ fontSize: 13.5, color: "var(--text-primary)", marginTop: 3, fontWeight: 500 }}>
              {facility.name}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 1 }}>{facility.location}</div>
          </div>
        )}

        <nav style={{ flex: 1, padding: "14px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
          {NAV_ITEMS.filter((item) => !item.permission || hasPermission(item.permission)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 11,
                padding: "10px 12px",
                borderRadius: "var(--radius-md)",
                fontSize: 14,
                fontWeight: 500,
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                background: isActive ? "var(--bg-surface-2)" : "transparent",
                borderLeft: isActive ? "2px solid var(--accent-oil)" : "2px solid transparent",
              })}
            >
              <item.icon />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-primary)" }}>{user?.full_name}</div>
              <div className="label-eyebrow" style={{ marginTop: 2 }}>
                {roleLabel(user?.role)}
              </div>
            </div>
            <button
              onClick={doLogout}
              title="Sign out"
              className="btn"
              style={{ padding: "7px 10px" }}
            >
              <LogoutIcon />
            </button>
          </div>
        </div>
      </aside>

      <main style={{ flex: 1, minWidth: 0, background: "var(--bg-base)" }}>
        <Outlet context={{ facility }} />
      </main>
    </div>
  );
}

function roleLabel(role) {
  const map = {
    ADMIN: "Administrator",
    PLANT_MANAGER: "Plant Manager",
    FEEDSTOCK_MANAGER: "Feedstock Manager",
    OPERATOR: "Operator",
    EXECUTIVE: "Executive",
  };
  return map[role] || role;
}

function LogoMark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
      <rect x="1" y="1" width="24" height="24" rx="6" fill="var(--bg-surface-2)" stroke="var(--border-strong)" />
      <path d="M8 18 L8 11 Q8 7 13 7 Q18 7 18 11 L18 14" stroke="var(--accent-oil)" strokeWidth="2" fill="none" strokeLinecap="round" />
      <circle cx="18" cy="17.5" r="2.2" fill="var(--accent-oil)" />
    </svg>
  );
}

function GaugeIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z" stroke="currentColor" strokeWidth="1.6" />
      <path d="M12 12 L16 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" />
    </svg>
  );
}
function LayersIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <path d="M12 3 L21 8 L12 13 L3 8 Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M3 13 L12 18 L21 13" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}
function BuildingIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <rect x="4" y="3" width="16" height="18" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <path d="M9 8h1M14 8h1M9 12h1M14 12h1M9 16h1M14 16h1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
function SlidersIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
      <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="9" cy="6" r="2" fill="var(--bg-surface)" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="16" cy="12" r="2" fill="var(--bg-surface)" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="11" cy="18" r="2" fill="var(--bg-surface)" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}
function LogoutIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
