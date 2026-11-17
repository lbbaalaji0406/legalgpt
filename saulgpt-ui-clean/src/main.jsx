import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import { API_BASE } from './apiConfig'
import './index.css'
import App from './App.jsx'

if (API_BASE) {
  axios.defaults.baseURL = API_BASE;
}

// Global interceptor to inject client-supplied Groq API key (BYOK)
axios.interceptors.request.use((config) => {
  const userGroqKey = localStorage.getItem("saulgpt_user_groq_key");
  if (userGroqKey && userGroqKey.trim()) {
    config.headers["X-Groq-Api-Key"] = userGroqKey.trim();
  }
  // Login token: sent in two headers (some proxies drop Authorization)
  const token = localStorage.getItem("saulgpt_token");
  if (token) {
    config.headers["X-SaulGPT-Token"] = token;
    if (!config.headers.Authorization) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global response interceptor to detect 429 Rate Limits
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.response?.data?.error || "";
    // Our own limiter ("Too many requests...") is not a Groq quota problem: no key dialog for it
    const ours = typeof detail === "string" && detail.startsWith("Too many requests");
    if (!ours && (status === 429 || (typeof detail === "string" && detail.toLowerCase().includes("rate limit")))) {
      window.dispatchEvent(new CustomEvent("saulgpt-rate-limit-hit", { detail: { error: detail } }));
    }
    // Expired or invalid login: sign out (login/signup 401s are just a wrong password)
    if (status === 401 && localStorage.getItem("saulgpt_token") && !String(error.config?.url || "").includes("/api/auth/")) {
      ["saulgpt_token", "saulgpt_user", "saulgpt_conv_id"].forEach((k) => localStorage.removeItem(k));
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
