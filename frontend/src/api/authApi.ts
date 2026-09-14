import { apiClient } from './client';
import { AuthConfig, AuthResponse, SignUpResponse, User, UserRole } from '../types';

export interface DemoTokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  claims: Record<string, any>;
}

export const authApi = {
  getAuthConfig: async (): Promise<AuthConfig> => {
    const res = await apiClient.get<AuthConfig>('/auth/config');
    return res.data;
  },

  login: async (username_or_email: string, password: string): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>('/auth/login', {
      username_or_email,
      password,
    });
    return res.data;
  },

  register: async (
    username: string,
    email: string,
    password: string,
    role: UserRole = 'user'
  ): Promise<SignUpResponse> => {
    const res = await apiClient.post<SignUpResponse>('/auth/register', {
      username,
      email,
      password,
      role,
    });
    return res.data;
  },

  confirmSignUp: async (username: string, confirmation_code: string): Promise<{ status: string; message: string }> => {
    const res = await apiClient.post<{ status: string; message: string }>('/auth/confirm-signup', {
      username,
      confirmation_code,
    });
    return res.data;
  },

  resendCode: async (username: string): Promise<SignUpResponse> => {
    const res = await apiClient.post<SignUpResponse>('/auth/resend-code', { username });
    return res.data;
  },

  forgotPassword: async (username_or_email: string): Promise<{ status: string; message: string; destination?: string }> => {
    const res = await apiClient.post<{ status: string; message: string; destination?: string }>('/auth/forgot-password', {
      username_or_email,
    });
    return res.data;
  },

  confirmForgotPassword: async (
    username: string,
    confirmation_code: string,
    new_password: string
  ): Promise<{ status: string; message: string }> => {
    const res = await apiClient.post<{ status: string; message: string }>('/auth/confirm-forgot-password', {
      username,
      confirmation_code,
      new_password,
    });
    return res.data;
  },

  getDemoToken: async (
    role: 'user' | 'admin' = 'user',
    username: string = 'alex_coder',
    email: string = 'alex@codegrid.dev'
  ): Promise<DemoTokenResponse> => {
    const res = await apiClient.post<DemoTokenResponse>('/auth/demo-token', {
      role,
      username,
      email,
    });
    return res.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  syncUser: async (username?: string): Promise<User> => {
    const res = await apiClient.post<User>('/auth/sync', username ? { username } : {});
    return res.data;
  },
};
