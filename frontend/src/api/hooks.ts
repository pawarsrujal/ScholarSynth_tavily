/**
 * React Query hooks for API interactions.
 */
import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { scholarApi, TaskState, StatusResponse, StreamEvent } from './client';

const isTaskState = (value: unknown): value is TaskState => {
  if (!value || typeof value !== 'object') return false;

  const task = value as Record<string, unknown>;
  return (
    typeof task.task_id === 'string' &&
    typeof task.query === 'string' &&
    typeof task.state === 'string' &&
    Array.isArray(task.sub_questions) &&
    Array.isArray(task.all_sources) &&
    Array.isArray(task.all_evidence)
  );
};

/**
 * Hook to create a new research report.
 */
export const useCreateReport = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (query: string) => scholarApi.createReport(query),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('reports');
      },
    }
  );
};

/**
 * Hook to fetch report status with polling.
 */
export const useReportStatus = (taskId: string | null, enabled = true) => {
  return useQuery<StatusResponse>(
    ['reportStatus', taskId],
    () => scholarApi.getStatus(taskId!),
    {
      enabled: enabled && !!taskId,
      refetchInterval: (data) => {
        if (!data || (data.status !== 'completed' && data.status !== 'failed')) {
          return 2000;
        }
        return false;
      },
    }
  );
};

/**
 * Hook to fetch the complete report.
 */
export const useReport = (taskId: string | null, enabled = true) => {
  return useQuery<TaskState>(
    ['report', taskId],
    () => scholarApi.getReport(taskId!),
    {
      enabled: enabled && !!taskId,
      refetchOnWindowFocus: false,
    }
  );
};

export const useTaskStream = (taskId: string | null) => {
  const [snapshot, setSnapshot] = useState<TaskState | null>(null);
  const [lastEvent, setLastEvent] = useState<StreamEvent | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!taskId) {
      setSnapshot(null);
      setLastEvent(null);
      setConnected(false);
      return;
    }

    const source = scholarApi.streamProgress(taskId);
    setConnected(true);

    const parseStreamEvent = (event: MessageEvent): StreamEvent | null => {
      try {
        return JSON.parse(event.data) as StreamEvent;
      } catch {
        return null;
      }
    };

    const applyTaskState = (event: MessageEvent) => {
      const payload = parseStreamEvent(event);
      if (!payload) return;
      setLastEvent(payload);
      if (isTaskState(payload.data)) {
        setSnapshot(payload.data);
      }
    };

    const handleGeneric = (event: MessageEvent) => {
      const payload = parseStreamEvent(event);
      if (payload) {
        setLastEvent(payload);
      }
    };

    const eventNames = [
      'task_started',
      'planning_started',
      'subquestions_created',
      'subquestion_started',
      'search_started',
      'source_found',
      'subquestion_completed',
      'verification_started',
      'publishing_started',
      'report_completed',
    ];

    eventNames.forEach((name) => source.addEventListener(name, handleGeneric as EventListener));
    source.addEventListener('snapshot', applyTaskState as EventListener);
    source.addEventListener('progress', applyTaskState as EventListener);
    source.addEventListener('error', (event) => {
      applyTaskState(event as MessageEvent);
      setConnected(false);
      source.close();
    });
    source.addEventListener('complete', (event) => {
      applyTaskState(event as MessageEvent);
      setConnected(false);
      source.close();
    });

    source.onerror = () => {
      setConnected(false);
      source.close();
    };

    return () => {
      eventNames.forEach((name) => source.removeEventListener(name, handleGeneric as EventListener));
      source.removeEventListener('snapshot', applyTaskState as EventListener);
      source.removeEventListener('progress', applyTaskState as EventListener);
      source.close();
    };
  }, [taskId]);

  return { snapshot, lastEvent, connected };
};

/**
 * Hook to delete a report.
 */
export const useDeleteReport = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (taskId: string) => scholarApi.deleteReport(taskId),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('reports');
      },
    }
  );
};
