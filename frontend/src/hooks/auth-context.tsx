import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiClient, { setAccessToken } from '@/lib/api-client';

export type UserRole = 'ADMIN' | 'CREDIT_RISK_GOVERNANCE_OFFICER';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchMe = async () => {
    try {
      const res = (await apiClient.get('/auth/me')) as any;
      if (res.success && res.data) {
        setUser(res.data);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
      setAccessToken(null);
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = (await apiClient.post('/auth/refresh', {
            refresh_token: refreshToken,
          })) as any;
          if (res.success && res.data) {
            const { access_token, refresh_token: newRefreshToken } = res.data;
            setAccessToken(access_token);
            localStorage.setItem('refresh_token', newRefreshToken);
            await fetchMe();
          }
        } catch {
          localStorage.removeItem('refresh_token');
          setAccessToken(null);
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = (await apiClient.post('/auth/login', { email, password })) as any;
      if (res.success && res.data) {
        const { access_token, refresh_token } = res.data;
        setAccessToken(access_token);
        localStorage.setItem('refresh_token', refresh_token);
        await fetchMe();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    const refreshToken = localStorage.getItem('refresh_token');
    try {
      if (refreshToken) {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken });
      }
    } catch (err) {
      console.error('Logout request failed', err);
    } finally {
      localStorage.removeItem('refresh_token');
      setAccessToken(null);
      setUser(null);
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
