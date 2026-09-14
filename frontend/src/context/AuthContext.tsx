import React, { createContext, useContext, useEffect, useState } from 'react';
import { AuthConfig, SignUpResponse, User, UserRole } from '../types';
import { authApi } from '../api/authApi';
import { isTokenExpired } from '../utils/jwt';

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
  loginWithGoogle: () => Promise<void>;
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

  // Initialize auth state: handle OAuth redirect callback & validate JWT token expiration
  useEffect(() => {
    const initAuth = async () => {
      // 1. Fetch Auth Gateway Configuration
      try {
        const config = await authApi.getAuthConfig();
        setAuthConfig(config);
      } catch (err) {
        console.warn('Failed to load auth config:', err);
      }

      // 2. Check for incoming OAuth redirect callback (e.g. from Cognito / Google)
      let initialToken: string | null = null;
      if (typeof window !== 'undefined') {
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
        const queryParams = new URLSearchParams(window.location.search);
        const oauthToken =
          hashParams.get('access_token') ||
          hashParams.get('id_token') ||
          queryParams.get('token') ||
          queryParams.get('access_token');

        if (oauthToken) {
          initialToken = oauthToken;
          localStorage.setItem('cyber_token', oauthToken);
          // Clean up the URL query/hash without causing a page refresh
          window.history.replaceState(null, '', window.location.pathname);
        }
      }

      // 3. Resolve Stored Token and verify expiration
      const storedToken = initialToken || localStorage.getItem('cyber_token');
      if (storedToken) {
        if (isTokenExpired(storedToken)) {
          console.warn('JWT token is expired or invalid. Resetting to guest session.');
          localStorage.removeItem('cyber_token');
          setUser(null);
          setToken(null);
        } else {
          try {
            const profile = await authApi.getCurrentUser();
            setUser(profile);
            setToken(storedToken);
          } catch (err) {
            console.warn('Session verification failed, logging out:', err);
            localStorage.removeItem('cyber_token');
            setUser(null);
            setToken(null);
          }
        }
      } else {
        // Default to clean unauthenticated guest session on home catalog
        setUser(null);
        setToken(null);
      }

      setIsLoading(false);
    };

    initAuth();
  }, []);

  // Listen for unauthorized 401 events dispatched by Axios interceptor
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
      localStorage.removeItem('cyber_token');
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
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

  const loginWithGoogle = async () => {
    if (authConfig?.cognito_domain && !authConfig.mock_cognito) {
      // Real AWS Cognito Hosted UI with Google IdP redirect
      const redirectUri = encodeURIComponent(window.location.origin);
      const clientId = authConfig.client_id || authConfig.user_pool_id;
      const cognitoUrl = `https://${authConfig.cognito_domain}/oauth2/authorize?identity_provider=Google&client_id=${clientId}&response_type=token&scope=email+openid+profile&redirect_uri=${redirectUri}`;
      window.location.href = cognitoUrl;
    } else {
      // Simulated Google OAuth session for development / mock environments
      setIsLoading(true);
      try {
        const demoRes = await authApi.getDemoToken('user', 'google_coder', 'coder@gmail.com');
        localStorage.setItem('cyber_token', demoRes.access_token);
        setToken(demoRes.access_token);
        const profile = await authApi.getCurrentUser();
        setUser(profile);
      } catch (err) {
        console.error('Failed Google OAuth login:', err);
      } finally {
        setIsLoading(false);
      }
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
        loginWithGoogle,
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
