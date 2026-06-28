import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function LoginPage() {
  const { doLogin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@plastiq.demo");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await doLogin(email, password);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-base)",
        backgroundImage:
          "radial-gradient(circle at 20% 20%, rgba(232,147,46,0.06), transparent 40%), radial-gradient(circle at 80% 80%, rgba(63,168,156,0.06), transparent 40%)",
      }}
    >
      <div style={{ width: 400 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: 38,
              letterSpacing: "0.01em",
            }}
          >
            PLASTI<span style={{ color: "var(--accent-oil)" }}>Q</span>
          </div>
          <div className="label-eyebrow" style={{ marginTop: 4 }}>
            Plastic Waste Detection &amp; Pyrolysis Yield Intelligence
          </div>
        </div>

        <form onSubmit={handleSubmit} className="card" style={{ padding: 28 }}>
          <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@plant.com"
            required
            style={{ marginBottom: 16 }}
          />

          <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            style={{ marginBottom: 18 }}
          />

          {error && (
            <div
              style={{
                background: "var(--accent-hazard-dim)",
                color: "var(--accent-hazard-bright)",
                fontSize: 13,
                padding: "9px 12px",
                borderRadius: "var(--radius-md)",
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          <button type="submit" className="btn btn-primary" disabled={submitting} style={{ width: "100%", justifyContent: "center", padding: "11px 16px" }}>
            {submitting ? "Signing in…" : "Sign In"}
          </button>

          <div
            style={{
              marginTop: 18,
              paddingTop: 16,
              borderTop: "1px solid var(--border)",
              fontSize: 12,
              color: "var(--text-tertiary)",
              lineHeight: 1.6,
            }}
          >
            <div className="label-eyebrow" style={{ marginBottom: 6 }}>
              Demo Accounts
            </div>
            admin@plastiq.demo · manager@plastiq.demo · operator@plastiq.demo · exec@plastiq.demo
            <br />
            Password: <span className="mono">ChangeMe123!</span>
          </div>
        </form>
      </div>
    </div>
  );
}
