import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import { API_BASE } from './apiConfig'
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
  return config;
});

// Global response interceptor to detect 429 Rate Limits
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.response?.data?.error || "";
    if (status === 429 || (typeof detail === "string" && detail.toLowerCase().includes("rate limit"))) {
      window.dispatchEvent(new CustomEvent("saulgpt-rate-limit-hit", { detail: { error: detail } }));
    }
    return Promise.reject(error);
  }
);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
