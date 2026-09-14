import axios from 'axios';

export const API_BASE_URL = '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT Token to every outgoing request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('cyber_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      // Optional: localStorage.removeItem('cyber_token');
    }
    return Promise.reject(error);
  }
);
