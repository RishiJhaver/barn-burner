import { apiClient } from './client';
import { Problem, Tag } from '../types';

export const problemsApi = {
  getProblems: async (params?: {
    difficulty?: string;
    tag_slug?: string;
    tag?: string;
    limit?: number;
    cursor?: string;
  }): Promise<{ items: Problem[]; next_cursor?: string | null; has_more: boolean }> => {
    const cleanParams: Record<string, any> = {};
    if (params?.difficulty && params.difficulty !== 'all') {
      cleanParams.difficulty = params.difficulty;
    }
    const resolvedTag = params?.tag || params?.tag_slug;
    if (resolvedTag && resolvedTag !== 'all') {
      cleanParams.tag = resolvedTag;
      cleanParams.tag_slug = resolvedTag;
    }
    if (params?.limit) cleanParams.limit = params.limit;
    if (params?.cursor) cleanParams.cursor = params.cursor;

    const res = await apiClient.get('/problems', { params: cleanParams });
    // Normalize response: if backend returns array directly or paginated wrapper
    if (Array.isArray(res.data)) {
      return { items: res.data, has_more: false };
    }
    return {
      items: res.data.items || [],
      next_cursor: res.data.next_cursor,
      has_more: !!res.data.has_more,
    };
  },

  getProblemBySlug: async (slug: string): Promise<Problem> => {
    const res = await apiClient.get<Problem>(`/problems/${slug}`);
    return res.data;
  },

  getTags: async (): Promise<Tag[]> => {
    const res = await apiClient.get<Tag[]>('/tags');
    return res.data;
  },
};
