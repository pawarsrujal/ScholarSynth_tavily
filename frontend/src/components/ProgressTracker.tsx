/**
 * Progress tracker component for research workflow.
 */
import React from 'react';
import { StatusResponse, SubQuestion } from '../api/client';
import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';

interface ProgressTrackerProps {
  status?: StatusResponse;
  subQuestions?: SubQuestion[];
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ status, subQuestions }) => {
  if (!status) return null;

  const getStatusIcon = (questionStatus: string) => {
    switch (questionStatus) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case 'searching':
      case 'retrieving':
      case 'analyzing':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Circle className="w-5 h-5 text-gray-300" />;
    }
  };

  const getStageIndex = (state: string) => {
    switch (state) {
      case 'planning':
        return 0;
      case 'searching':
      case 'retrieving':
      case 'analyzing':
        return 1;
      case 'verifying':
        return 2;
      case 'publishing':
        return 3;
      case 'completed':
        return 4;
      default:
        return 0;
    }
  };

  const stages = [
    { id: 'planning', label: 'Planning' },
    { id: 'searching', label: 'Research' },
    { id: 'verifying', label: 'Verification' },
    { id: 'publishing', label: 'Publishing' },
  ];
  const activeStage = getStageIndex(status.state);

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Research Progress</h3>
          <span className="text-sm font-medium text-gray-600">
            {status.progress_percentage}%
          </span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ease-out ${status.state === 'failed' ? 'bg-red-500' : 'bg-primary-600'}`}
            style={{ width: `${status.progress_percentage}%` }}
          />
        </div>

        <p className="text-sm text-gray-600">{status.current_step}</p>
      </div>

      {/* Stage Indicators */}
      <div className="grid gap-3 md:grid-cols-4">
        {stages.map((stage, index) => (
          <div key={stage.id} className="flex items-center">
            <div className="flex flex-col items-start w-full">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${index <= activeStage ? 'bg-primary-600' : 'bg-gray-200'}`}
              >
                {index === activeStage && status.state !== 'completed' && status.state !== 'failed' ? (
                  <Loader2 className="w-5 h-5 text-white animate-spin" />
                ) : (
                  <span className="text-white font-semibold">{index + 1}</span>
                )}
              </div>
              <span className="text-xs mt-2 capitalize">{stage.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-2 md:grid-cols-4">
        {stages.map((stage, index) => (
          <div key={stage.id} className="space-y-1">
            <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
              <div className={`h-full ${index <= activeStage ? 'bg-primary-600' : 'bg-transparent'}`} style={{ width: index < activeStage ? '100%' : index === activeStage ? '70%' : '0%' }} />
            </div>
            <p className="text-xs text-gray-500">{stage.label}</p>
          </div>
        ))}
      </div>

      {/* Sub-questions List */}
      {subQuestions && subQuestions.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold text-gray-900">Research Questions</h4>
          <div className="space-y-2">
            {subQuestions.map((q, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200"
              >
                <div className="mt-0.5">{getStatusIcon(q.status)}</div>
                <div className="flex-1">
                  <p className="text-sm text-gray-800">
                    <span className="font-semibold">[{q.id}]</span> {q.question}
                  </p>
                  {q.status === 'completed' && q.sources.length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      {q.sources.length} sources found
                    </p>
                  )}
                  {q.error && <p className="text-xs text-red-500 mt-1">{q.error}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
