/**
 * API client for ScholarSynth backend.
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export interface Citation {
  id: string;
  title: string;
  url: string;
  snippet?: string;
  published_date?: string;
  domain?: string;
  score?: number;
  content?: string;
}

export interface SubQuestion {
  id: string;
  question: string;
  search_queries: string[];
  status: 'pending' | 'searching' | 'retrieving' | 'analyzing' | 'completed' | 'failed';
  summary?: string;
  sources: Citation[];
  evidence?: Evidence[];
  error?: string;
}

export interface Evidence {
  claim: string;
  supporting_text: string;
  source_ids: string[];
  confidence: number;
  valid?: boolean;
  reason?: string;
}

export interface Report {
  title: string;
  summary: string;
  content: string;
  word_count: number;
  citation_count: number;
  sources: Citation[];
  generated_at: string;
}

export interface TaskState {
  task_id: string;
  query: string;
  state: 'planning' | 'searching' | 'retrieving' | 'analyzing' | 'verifying' | 'publishing' | 'completed' | 'failed';
  sub_questions: SubQuestion[];
  source_registry?: Record<string, Citation>;
  all_sources?: Citation[];
  all_evidence?: Evidence[];
  report?: Report;
  error?: string;
  created_at: string;
  updated_at: string;
  current_step: string;
  progress_percentage: number;
}

export interface StatusResponse {
  task_id: string;
  state: string;
  status: string;
  current_step: string;
  progress_percentage: number;
  sub_questions: SubQuestion[];
  sub_questions_count: number;
  completed_questions: number;
  error?: string;
}

export interface CreateReportRequest {
  query: string;
}

export interface CreateReportResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface StreamEvent {
  event: string;
  task_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const scholarApi = {
  /**
   * Create a new research report task.
   */
  createReport: async (query: string): Promise<CreateReportResponse> => {
    const response = await api.post<CreateReportResponse>('/api/report', { query });
    return response.data;
  },

  /**
   * Get status of a research task.
   */
  getStatus: async (taskId: string): Promise<StatusResponse> => {
    const response = await api.get<StatusResponse>(`/api/report/${taskId}/status`);
    return response.data;
  },

  /**
   * Get the complete task state including the final report.
   */
  getReport: async (taskId: string): Promise<TaskState> => {
    const response = await api.get<TaskState>(`/api/report/${taskId}`);
    return response.data;
  },

  /**
   * Create an EventSource for streaming progress updates.
   */
  streamProgress: (taskId: string): EventSource => {
    return new EventSource(`${API_BASE_URL}/api/report/${taskId}/stream`);
  },

  /**
   * Delete a report task.
   */
  deleteReport: async (taskId: string): Promise<void> => {
    await api.delete(`/api/report/${taskId}`);
  },
};
