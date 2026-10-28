/**
 * Report display component with markdown rendering.
 */
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Report as ReportType } from '../api/client';
import { Download, Copy, CheckCheck } from 'lucide-react';

interface ReportDisplayProps {
  report: ReportType;
}

export const ReportDisplay: React.FC<ReportDisplayProps> = ({ report }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(report.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([report.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title.replace(/[^a-z0-9]/gi, '_')}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Header with actions */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{report.title}</h2>
          <p className="text-sm text-gray-500 mt-1">
            {report.word_count.toLocaleString()} words • {report.citation_count} citations • {report.sources.length} sources •
            Generated {new Date(report.generated_at).toLocaleDateString()}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-sm"
          >
            {copied ? (
              <>
                <CheckCheck className="w-4 h-4" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </button>

          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors text-sm"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>
      </div>

      {/* Report Content */}
      <div className="prose prose-lg max-w-none">
        <ReactMarkdown
          components={{
            h1: ({ ...props }) => <h1 className="text-3xl font-bold mt-8 mb-4" {...props} />,
            h2: ({ ...props }) => <h2 className="text-2xl font-bold mt-6 mb-3" {...props} />,
            h3: ({ ...props }) => <h3 className="text-xl font-semibold mt-4 mb-2" {...props} />,
            p: ({ ...props }) => <p className="mb-4 leading-relaxed text-gray-700" {...props} />,
            ul: ({ ...props }) => <ul className="list-disc pl-6 mb-4 space-y-2" {...props} />,
            ol: ({ ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-2" {...props} />,
            li: ({ ...props }) => <li className="text-gray-700" {...props} />,
            a: ({ ...props }) => (
              <a
                className="text-primary-600 hover:text-primary-700 underline"
                target="_blank"
                rel="noopener noreferrer"
                {...props}
              />
            ),
            blockquote: ({ ...props }) => (
              <blockquote className="border-l-4 border-primary-500 pl-4 italic my-4 text-gray-600" {...props} />
            ),
          }}
        >
          {report.content}
        </ReactMarkdown>
      </div>

      {/* Citations (if not already in content) */}
      {report.sources.length > 0 && !report.content.includes('## Sources') && (
        <div className="mt-8 pt-6 border-t border-gray-200">
          <h3 className="text-xl font-bold mb-4">Sources</h3>
          <div className="space-y-3">
            {report.sources.map((citation) => (
              <div key={citation.id} className="text-sm">
                <span className="font-semibold">[{citation.id}]</span>{' '}
                <span className="italic">{citation.title}.</span>{' '}
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-600 hover:underline"
                >
                  {citation.url}
                </a>
                {citation.published_date && <span>. {citation.published_date}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
