import { createContext, useContext, useEffect, useState } from "react";
import * as endpoints from "../api/endpoints";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem("plastiq_user");
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("plastiq_token");
    if (!token) {
      setLoading(false);
      return;
    }
    endpoints
      .getMe()
      .then((res) => {
        setUser(res.data);
        localStorage.setItem("plastiq_user", JSON.stringify(res.data));
      })
      .catch(() => {
        localStorage.removeItem("plastiq_token");
        localStorage.removeItem("plastiq_user");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const doLogin = async (email, password) => {
    const res = await endpoints.login(email, password);
    localStorage.setItem("plastiq_token", res.data.access_token);
    localStorage.setItem("plastiq_user", JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  };

  const doLogout = () => {
    localStorage.removeItem("plastiq_token");
    localStorage.removeItem("plastiq_user");
    setUser(null);
  };

  const hasPermission = (permission) => {
    if (!user) return false;
    const matrix = {
      ADMIN: [
        "manage_users", "configure_facilities", "configure_lines", "configure_pricing",
        "configure_ai_settings", "view_all_reports", "view_dashboards", "view_kpis",
        "view_bi_reports", "create_runs", "view_forecasts", "monitor_operations",
        "approve_schedules", "manage_stock", "receive_materials", "issue_materials",
        "monitor_inventory", "update_machine_status", "record_production",
        "submit_reports", "trigger_detection", "view_detections",
      ],
      PLANT_MANAGER: [
        "create_runs", "view_forecasts", "monitor_operations", "approve_schedules",
        "view_dashboards", "view_kpis", "trigger_detection", "view_detections", "monitor_inventory",
      ],
      FEEDSTOCK_MANAGER: [
        "manage_stock", "receive_materials", "issue_materials", "monitor_inventory",
        "view_detections", "view_dashboards",
      ],
      OPERATOR: [
        "update_machine_status", "record_production", "submit_reports",
        "trigger_detection", "view_detections",
      ],
      EXECUTIVE: ["view_dashboards", "view_kpis", "view_bi_reports", "view_all_reports", "view_forecasts"],
    };
    return (matrix[user.role] || []).includes(permission);
  };

  return (
    <AuthContext.Provider value={{ user, loading, doLogin, doLogout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
