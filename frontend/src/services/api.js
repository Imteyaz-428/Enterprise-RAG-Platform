import axios from "axios";
import toast from "react-hot-toast";
import {
  getToken,
  getRefreshToken,
  saveToken,
  saveRefreshToken,
  clearTokens,
} from "../utils/token";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
});

api.interceptors.request.use(
  (config) => {
    const token = getToken();

    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response ? error.response.status : null;

    const url = originalRequest?.url || "";
    const isAuthRoute =
      url.includes("/auth/login") || url.includes("/auth/refresh");

    // 401 handling: single in-flight POST /auth/refresh, retry once, skip login/refresh routes
    if (status === 401 && !isAuthRoute) {
      if (!originalRequest._retry) {
        originalRequest._retry = true;

        const refreshToken = getRefreshToken();
        if (!refreshToken) {
          clearTokens();
          if (
            window.location.pathname !== "/login" &&
            window.location.pathname !== "/"
          ) {
            window.location.href = "/login";
          }
          return Promise.reject(error);
        }

        if (!refreshPromise) {
          const refreshUrl = `${api.defaults.baseURL || ""}/auth/refresh`;
          refreshPromise = axios
            .post(
              refreshUrl,
              { refresh_token: refreshToken },
              { headers: { "Content-Type": "application/json" } }
            )
            .then((res) => {
              const newAccessToken = res.data.access_token;
              saveToken(newAccessToken);
              if (res.data.refresh_token) {
                saveRefreshToken(res.data.refresh_token);
              }
              return newAccessToken;
            })
            .catch((refreshErr) => {
              clearTokens();
              if (
                window.location.pathname !== "/login" &&
                window.location.pathname !== "/"
              ) {
                window.location.href = "/login";
              }
              return Promise.reject(refreshErr);
            })
            .finally(() => {
              refreshPromise = null;
            });
        }

        return refreshPromise.then((token) => {
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }
    }

    // Centralized toast messages for specific error codes
    if (status === 403) {
      toast.error("You do not have permission");
    } else if (status === 409) {
      const detail = error.response?.data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : "Conflict error occurred.";
      toast.error(message);
    } else if (status === 503) {
      toast.error("Service temporarily unavailable, try again");
    }

    return Promise.reject(error);
  }
);

export default api;
