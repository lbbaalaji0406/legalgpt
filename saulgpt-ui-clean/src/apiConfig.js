// Centralized API Base URL configuration for SaulGPT
// In local development or with Cloud Run / Firebase rewrite, defaults to ""
// If deployed with a standalone backend (Render, Railway, Cloud Run), set VITE_API_BASE
export const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/+$/, "");
