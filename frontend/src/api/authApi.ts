import { apiClient } from './client';
import { User } from '../types';

export interface DemoTokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  claims: Record<string, any>;
}

export const authApi = {
  getDemoToken: async (
    role: 'user' | 'admin' = 'user',
    username: string = 'cyber_coder',
    email: string = 'coder@matrix.cyber'
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
