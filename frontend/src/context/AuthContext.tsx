import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, UserRole } from '../types';
import { authApi } from '../api/authApi';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  loginDemo: (role?: UserRole, username?: string, email?: string) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('cyber_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('cyber_token');
      if (storedToken) {
        try {
          const profile = await authApi.getCurrentUser();
          setUser(profile);
          setToken(storedToken);
          setIsLoading(false);
          return;
        } catch (err) {
          console.warn('Stored token invalid, auto-generating demo session...');
        }
      }
      // Auto-login with default Coder demo account on first visit
      await loginDemo('user', 'neo_coder', 'neo@cybercode.matrix');
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const loginDemo = async (
    role: UserRole = 'user',
    username: string = 'neo_coder',
    email: string = 'neo@cybercode.matrix'
  ) => {
    setIsLoading(true);
    try {
      const demoRes = await authApi.getDemoToken(role, username, email);
      localStorage.setItem('cyber_token', demoRes.access_token);
      setToken(demoRes.access_token);
      const profile = await authApi.getCurrentUser();
      setUser(profile);
    } catch (err) {
      console.error('Failed demo login:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithToken = async (newToken: string) => {
    setIsLoading(true);
    try {
      localStorage.setItem('cyber_token', newToken);
      setToken(newToken);
      const profile = await authApi.getCurrentUser();
      setUser(profile);
    } catch (err) {
      console.error('Failed to authenticate token:', err);
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('cyber_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        loginDemo,
        loginWithToken,
        logout,
        isAdmin: user?.role === 'admin',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
