import api from "./client";

// ---- Auth ----
export const login = (email, password) => api.post("/auth/login", { email, password });
export const register = (payload) => api.post("/auth/register", payload);
export const getMe = () => api.get("/auth/me");
export const listUsers = () => api.get("/auth/users");

// ---- Facilities ----
export const listFacilities = () => api.get("/facilities");
export const createFacility = (payload) => api.post("/facilities", payload);
export const getFacility = (id) => api.get(`/facilities/${id}`);
export const listScanSources = (facilityId) => api.get(`/facilities/${facilityId}/scan-sources`);
export const createScanSource = (payload) => api.post("/facilities/scan-sources", payload);
export const getAISettings = (facilityId) => api.get(`/facilities/${facilityId}/ai-settings`);
export const updateAISettings = (facilityId, payload) =>
  api.patch(`/facilities/${facilityId}/ai-settings`, payload);

// ---- Waste & Detection ----
export const listBatches = (facilityId) =>
  api.get("/waste/batches", { params: facilityId ? { facility_id: facilityId } : {} });
export const getBatch = (id) => api.get(`/waste/batches/${id}`);
export const createBatch = (payload) => api.post("/waste/batches", payload);
export const uploadImage = (batchId, file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post(`/waste/batches/${batchId}/upload-image`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const runDetection = (payload) => api.post("/waste/detect", payload);
export const listDetectionRuns = (batchId) => api.get(`/waste/batches/${batchId}/detection-runs`);
export const getBatchComposition = (batchId) => api.get(`/waste/batches/${batchId}/composition`);

// ---- Reports ----
export const generateReport = (payload) => api.post("/reports/generate", payload);
export const getReport = (id) => api.get(`/reports/${id}`);
export const getReportsForBatch = (batchId) => api.get(`/reports/batch/${batchId}`);

// ---- Dashboard ----
export const getDashboard = (facilityId, limit) =>
  api.get("/dashboard", { params: { facility_id: facilityId, limit: limit || 30 } });
