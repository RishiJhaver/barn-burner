import React, { createContext, useContext, useEffect, useState } from 'react';
import { AuthConfig, SignUpResponse, User, UserRole } from '../types';
import { authApi } from '../api/authApi';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  authConfig: AuthConfig | null;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, role?: UserRole) => Promise<SignUpResponse>;
  confirmSignUp: (username: string, code: string) => Promise<{ status: string; message: string }>;
  resendCode: (username: string) => Promise<SignUpResponse>;
  forgotPassword: (usernameOrEmail: string) => Promise<{ status: string; message: string; destination?: string }>;
  confirmForgotPassword: (username: string, code: string, newPassword: string) => Promise<{ status: string; message: string }>;
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
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);

  // Initialize auth state and fetch config
  useEffect(() => {
    const initAuth = async () => {
      // 1. Fetch Auth Gateway Configuration
      try {
        const config = await authApi.getAuthConfig();
        setAuthConfig(config);
      } catch (err) {
        console.warn('Failed to load auth config:', err);
      }

      // 2. Resolve Stored Token
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
      await loginDemo('user', 'alex_coder', 'alex@codegrid.dev');
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (usernameOrEmail: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(usernameOrEmail, password);
      localStorage.setItem('cyber_token', res.access_token);
      setToken(res.access_token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (username: string, email: string, password: string, role: UserRole = 'user') => {
    return await authApi.register(username, email, password, role);
  };

  const confirmSignUp = async (username: string, code: string) => {
    return await authApi.confirmSignUp(username, code);
  };

  const resendCode = async (username: string) => {
    return await authApi.resendCode(username);
  };

  const forgotPassword = async (usernameOrEmail: string) => {
    return await authApi.forgotPassword(usernameOrEmail);
  };

  const confirmForgotPassword = async (username: string, code: string, newPassword: string) => {
    return await authApi.confirmForgotPassword(username, code, newPassword);
  };

  const loginDemo = async (
    role: UserRole = 'user',
    username: string = 'alex_coder',
    email: string = 'alex@codegrid.dev'
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
        authConfig,
        login,
        register,
        confirmSignUp,
        resendCode,
        forgotPassword,
        confirmForgotPassword,
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
