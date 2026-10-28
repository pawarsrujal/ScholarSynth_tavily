/**
 * Main query page component.
 */
import React, { useMemo, useState } from 'react';
import { useCreateReport, useReportStatus, useReport, useTaskStream } from '../api/hooks';
import { ProgressTracker } from '../components/ProgressTracker';
import { ReportDisplay } from '../components/ReportDisplay';
import { SourceList } from '../components/SourceList';
import { Search, Sparkles, AlertCircle, Wifi, WifiOff } from 'lucide-react';

export const QueryPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);

  const createReport = useCreateReport();
  const { snapshot, connected } = useTaskStream(currentTaskId);
  const { data: status } = useReportStatus(currentTaskId, !!currentTaskId);
  const shouldFetchReport = !!currentTaskId && (snapshot?.state === 'completed' || status?.status === 'completed');
  const { data: fetchedTask } = useReport(currentTaskId, shouldFetchReport);

  const statusTask = useMemo(() => {
    if (!status) return null;
    return {
      task_id: status.task_id,
      query,
      state: status.state as any,
      sub_questions: status.sub_questions ?? [],
      source_registry: {},
      all_sources: [],
      all_evidence: [],
      report: undefined,
      error: status.error,
      created_at: '',
      updated_at: '',
      current_step: status.current_step,
      progress_percentage: status.progress_percentage,
    };
  }, [query, status]);

  const isStatusTerminal = status?.status === 'failed' || status?.status === 'completed';
  const task = (isStatusTerminal && statusTask ? (fetchedTask ?? statusTask) : snapshot) ?? fetchedTask ?? statusTask ?? null;
  const liveStatus = task
    ? {
        task_id: task.task_id,
        state: task.state,
        status: task.state,
        current_step: task.current_step,
        progress_percentage: task.progress_percentage,
        sub_questions: task.sub_questions,
        sub_questions_count: task.sub_questions.length,
        completed_questions: task.sub_questions.filter((q) => q.status === 'completed').length,
        error: task.error,
      }
    : status;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) return;

    try {
      const result = await createReport.mutateAsync(query);
      setCurrentTaskId(result.task_id);
    } catch (error) {
      console.error('Failed to create report:', error);
    }
  };

  const handleReset = () => {
    setQuery('');
    setCurrentTaskId(null);
  };

  const isProcessing = currentTaskId && liveStatus?.status !== 'completed' && liveStatus?.status !== 'failed';
  const isDone = liveStatus?.status === 'completed';
  const isFailed = liveStatus?.status === 'failed';
  const sources = task?.all_sources ?? task?.report?.sources ?? [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">ScholarSynth</h1>
              <p className="text-sm text-gray-600">AI-Powered Deep Research System</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="space-y-8">
          {/* Query Input */}
          {!currentTaskId && (
            <div className="card max-w-3xl mx-auto">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                What would you like to research?
              </h2>
              <p className="text-gray-600 mb-6">
                Enter your research question and our AI agents will generate a comprehensive
                2000+ word report with citations from multiple sources.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="E.g., What are the latest advances in quantum computing and their implications for cryptography?"
                    className="input-field min-h-[120px] resize-none"
                    disabled={createReport.isLoading}
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Tip: Be specific and include context for better results
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={!query.trim() || createReport.isLoading}
                  className="btn-primary w-full flex items-center justify-center gap-2 py-3"
                >
                  <Search className="w-5 h-5" />
                  {createReport.isLoading ? 'Starting Research...' : 'Generate Research Report'}
                </button>
              </form>

              {/* Example queries */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <p className="text-sm font-semibold text-gray-700 mb-3">Example queries:</p>
                <div className="space-y-2">
                  {[
                    'What are the environmental impacts of blockchain technology?',
                    'How is CRISPR gene editing being used in cancer treatment?',
                    'What are the ethical implications of AI in autonomous vehicles?',
                  ].map((example, i) => (
                    <button
                      key={i}
                      onClick={() => setQuery(example)}
                      className="text-left text-sm text-primary-600 hover:text-primary-700 hover:underline block"
                    >
                      → {example}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Progress Tracking */}
          {isProcessing && (
            <div className="card space-y-4">
              <div className="flex items-center justify-between text-sm text-gray-600">
                <span className="flex items-center gap-2">
                  {connected ? <Wifi className="w-4 h-4 text-green-500" /> : <WifiOff className="w-4 h-4 text-amber-500" />}
                  {connected ? 'Live SSE connected' : 'Waiting for live updates'}
                </span>
                {currentTaskId && <span className="font-mono text-xs">Task {currentTaskId.slice(0, 8)}…</span>}
              </div>
              <ProgressTracker
                status={liveStatus as any}
                subQuestions={task?.sub_questions}
              />
              <SourceList sources={sources} title={`Sources Found: ${sources.length}`} />
            </div>
          )}

          {/* Error Display */}
          {isFailed && (
            <div className="card bg-red-50 border-red-200">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-red-600 mt-1" />
                <div>
                  <h3 className="font-semibold text-red-900">Research Failed</h3>
                  <p className="text-red-700 mt-1">{task?.error || 'An unknown error occurred'}</p>
                  <button
                    onClick={handleReset}
                    className="btn-secondary mt-4"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Final Report */}
          {isDone && task?.report && (
            <div className="space-y-4">
              <div className="card bg-green-50 border-green-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Sparkles className="w-6 h-6 text-green-600" />
                    <div>
                      <h3 className="font-semibold text-green-900">Research Complete!</h3>
                      <p className="text-sm text-green-700">
                        Your comprehensive report is ready
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleReset}
                    className="btn-secondary"
                  >
                    New Research
                  </button>
                </div>
              </div>

              <div className="card">
                <ReportDisplay report={task.report} />
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-16 py-6 border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-600">
          <p>
            ScholarSynth • Powered by LangGraph + OpenRouter / Groq / Gemini •
            All data is in-memory and cleared on restart
          </p>
        </div>
      </footer>
    </div>
  );
};
