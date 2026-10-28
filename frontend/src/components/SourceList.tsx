import React from 'react'
import { ExternalLink, Link2 } from 'lucide-react'
import { Citation } from '../api/client'

interface SourceListProps {
    sources: Citation[]
    title?: string
}

export const SourceList: React.FC<SourceListProps> = ({ sources, title = 'Sources Found' }) => {
    if (!sources.length) return null

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
                <span className="text-sm text-gray-500">{sources.length} sources</span>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
                {sources.map((source) => (
                    <a
                        key={source.id}
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="group block rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-all hover:border-primary-300 hover:shadow-md"
                    >
                        <div className="flex items-start gap-3">
                            <div className="mt-1 rounded-lg bg-primary-50 p-2 text-primary-600">
                                <Link2 className="h-4 w-4" />
                            </div>
                            <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-semibold text-primary-700">[{source.id}]</span>
                                    <h4 className="truncate font-semibold text-gray-900">{source.title}</h4>
                                </div>
                                <p className="mt-1 text-xs text-gray-500 truncate">{source.domain || source.url}</p>
                                {source.snippet && <p className="mt-2 line-clamp-3 text-sm text-gray-600">{source.snippet}</p>}
                                <div className="mt-3 flex items-center gap-2 text-xs text-primary-600 opacity-80 group-hover:opacity-100">
                                    <ExternalLink className="h-3.5 w-3.5" />
                                    Open source
                                </div>
                            </div>
                        </div>
                    </a>
                ))}
            </div>
        </div>
    )
}
