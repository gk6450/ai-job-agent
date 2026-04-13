import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

/* ─── Types ─── */

export interface ApplicationStats {
  total: number;
  active: number;
  interviews: number;
  pending_followups: number;
  by_status: Record<string, number>;
  by_date: { date: string; count: number }[];
  recent_activity: {
    id: string;
    company: string;
    role: string;
    action: string;
    timestamp: string;
  }[];
}

export interface Application {
  id: string;
  company: string;
  role: string;
  platform: string;
  status: string;
  applied_date: string;
  location?: string;
  salary?: string;
  notes?: string;
  url?: string;
}

export interface JobResult {
  title: string;
  company: string;
  location: string;
  salary?: string;
  platform: string;
  url: string;
  description?: string;
  posted_date?: string;
}

export interface SearchParams {
  keywords: string;
  location: string;
  platforms: string[];
  experience_level: string;
  remote_only: boolean;
}

export interface GeneratedDoc {
  filename: string;
  doc_type: string;
  company: string;
  role: string;
  created_at: string;
}

export interface TailorRequest {
  job_description: string;
  job_title: string;
  company: string;
  application_id?: string;
}

export interface Profile {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin?: string;
  github?: string;
}

export interface Preferences {
  target_roles: string[];
  target_locations: string[];
  min_salary: number;
  max_salary: number;
  remote_only: boolean;
  followup_days: number;
  auto_sync: boolean;
}

export interface ConnectionStatus {
  name: string;
  connected: boolean;
  last_sync?: string;
}

export interface GmailResponse {
  id: string;
  company: string;
  subject: string;
  snippet: string;
  date: string;
  status: string;
}

/* ─── API Functions ─── */

export const checkHealth = () => api.get("/health");

export const getApplications = (status?: string) =>
  api.get<Application[]>("/applications", { params: status ? { status } : {} });

export const getApplicationStats = () =>
  api.get<ApplicationStats>("/applications/stats");

export const getFollowups = () =>
  api.get<Application[]>("/applications/followups");

export const getApplication = (id: string) =>
  api.get<Application>(`/applications/${id}`);

export const updateApplicationStatus = (
  id: string,
  data: { status: string; notes?: string }
) => api.put(`/applications/${id}/status`, data);

export const searchJobs = (params: SearchParams) =>
  api.post<{ results: JobResult[] }>("/search", params);

export const getGeneratedDocs = () =>
  api.get<GeneratedDoc[]>("/resume/generated");

export const downloadDoc = (docType: string, filename: string) =>
  `/api/resume/download/${docType}/${filename}`;

export const tailorResume = (data: TailorRequest) =>
  api.post("/resume/tailor", data);

export const getGmailStatus = () =>
  api.get<{ connected: boolean; email?: string }>("/gmail/status");

export const syncGmail = () => api.post("/gmail/sync");

export const getGmailResponses = () =>
  api.get<GmailResponse[]>("/gmail/responses");

export const getProfile = () => api.get<Profile>("/settings/profile");

export const updateProfile = (data: Profile) =>
  api.put("/settings/profile", data);

export const getPreferences = () =>
  api.get<Preferences>("/settings/preferences");

export const updatePreferences = (data: Preferences) =>
  api.put("/settings/preferences", data);

export const getConnections = () =>
  api.get<ConnectionStatus[]>("/settings/connections");

export default api;
