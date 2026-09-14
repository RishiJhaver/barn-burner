import { apiClient } from './client';
import {
  SubmissionAcceptedResponse,
  SubmissionDetail,
  UserStats,
} from '../types';

export const submissionsApi = {
  runCode: async (
    slug: string,
    language: string,
    code: string,
    customInput?: string
  ): Promise<SubmissionAcceptedResponse> => {
    const res = await apiClient.post<SubmissionAcceptedResponse>(
      `/problems/${slug}/run`,
      {
        language,
        code,
        custom_input: customInput,
      }
    );
    return res.data;
  },

  submitCode: async (
    slug: string,
    language: string,
    code: string
  ): Promise<SubmissionAcceptedResponse> => {
    const res = await apiClient.post<SubmissionAcceptedResponse>(
      `/problems/${slug}/submit`,
      {
        language,
        code,
      }
    );
    return res.data;
  },

  getSubmission: async (id: string): Promise<SubmissionDetail> => {
    const res = await apiClient.get<SubmissionDetail>(`/submissions/${id}`);
    return res.data;
  },

  getSubmissionsHistory: async (params?: {
    problem_slug?: string;
    status?: string;
    language?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: SubmissionDetail[]; total: number }> => {
    const res = await apiClient.get<SubmissionDetail[]>('/submissions', {
      params,
    });
    const totalCount = parseInt(res.headers['x-total-count'] || '0', 10);
    return {
      items: Array.isArray(res.data) ? res.data : [],
      total: totalCount || (Array.isArray(res.data) ? res.data.length : 0),
    };
  },

  getUserStats: async (): Promise<UserStats> => {
    const res = await apiClient.get<UserStats>('/submissions/stats');
    return res.data;
  },
};
