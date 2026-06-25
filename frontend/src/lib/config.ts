/** Base URL of the FastAPI backend. Override with VITE_API_BASE_URL at build/dev time. */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
