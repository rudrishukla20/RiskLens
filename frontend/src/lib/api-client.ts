import axios from 'axios';

let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

export const getAccessToken = () => accessToken;

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => {
    if (accessToken && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => {
    const envelope = response.data;
    if (envelope && typeof envelope === 'object' && 'success' in envelope) {
      if (envelope.success) {
        return envelope;
      } else {
        return Promise.reject(envelope.error || { code: 'UNKNOWN_ERROR', message: envelope.message });
      }
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
          });
          const envelope = res.data;
          if (envelope?.success && envelope.data) {
            const { access_token, refresh_token: newRefreshToken } = envelope.data;
            setAccessToken(access_token);
            localStorage.setItem('refresh_token', newRefreshToken);
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
            return apiClient(originalRequest);
          }
        } catch (refreshError) {
          localStorage.removeItem('refresh_token');
          setAccessToken(null);
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    
    const errorData = error.response?.data?.error;
    if (errorData) {
      return Promise.reject(errorData);
    }
    
    return Promise.reject({
      code: 'NETWORK_ERROR',
      message: error.message || 'A network error occurred.',
    });
  }
);

export default apiClient;
