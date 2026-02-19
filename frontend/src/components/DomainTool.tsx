'use client';

import { useState } from 'react';
import { api, type DomainAnalysis } from '@/lib/api';
import { Search, Globe, Shield, Clock, FileText, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

export default function DomainTool() {
    const [domain, setDomain] = useState('');
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<DomainAnalysis | null>(null);
    const [error, setError] = useState('');

    const analyze = async () => {
        if (!domain) return;
        setLoading(true);
        setError('');
        setData(null);
        try {
            const res = await api.analyzeDomain(domain);
            setData(res);
        } catch (err: any) {
            setError(err.message || 'Analysis failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-card border border-border rounded-xl p-8 shadow-2xl relative overflow-hidden">
            <div className="flex gap-4 mb-8">
                <input
                    type="text"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && analyze()}
                    placeholder="example.com"
                    className="flex-1 bg-surface border border-border rounded-lg px-4 py-3 text-foreground focus:border-green outline-none transition-colors placeholder:text-muted"
                />
                <button
                    onClick={analyze}
                    disabled={loading}
                    className="bg-green text-background font-bold px-8 py-3 rounded-lg hover:bg-green-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {loading ? <div className="w-5 h-5 border-2 border-background border-t-transparent rounded-full animate-spin" /> : 'Analyze'}
                </button>
            </div>

            {error && (
                <div className="bg-red/10 border border-red/20 text-red p-4 rounded-lg mb-6">
                    {error}
                </div>
            )}

            {data && (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex items-center gap-6 bg-surface p-6 rounded-xl mb-6">
                        <div className="text-center">
                            <div className={`text-5xl font-black mb-1 ${data.seo_score >= 70 ? 'text-green' : data.seo_score >= 40 ? 'text-yellow' : 'text-red'}`}>
                                {data.seo_score}
                            </div>
                            <div className="text-xs text-muted uppercase tracking-wider">SEO Score</div>
                        </div>
                        <div className="h-16 w-px bg-border/50" />
                        <div>
                            <h2 className="text-xl font-bold mb-2">{data.domain}</h2>
                            <div className="flex gap-4 text-sm text-muted">
                                <span className="flex items-center gap-1">
                                    {data.has_ssl ? <Shield size={14} className="text-green" /> : <AlertTriangle size={14} className="text-red" />}
                                    {data.has_ssl ? 'HTTPS Secure' : 'Not Secure'}
                                </span>
                                <span className="flex items-center gap-1">
                                    <Clock size={14} />
                                    {data.load_time_seconds}s load
                                </span>
                                <span className="flex items-center gap-1">
                                    <FileText size={14} />
                                    {data.word_count} words
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <MetaItem label="Title Tag" value={data.title || 'Missing'} status={data.title ? 'good' : 'bad'} />
                        <MetaItem label="Title Length" value={`${data.title_length} chars`} status={data.title_length >= 10 && data.title_length <= 70 ? 'good' : 'warn'} />
                        <MetaItem label="Meta Description" value={data.meta_description || 'Missing'} status={data.meta_description ? 'good' : 'bad'} truncate />
                        <MetaItem label="H1 Count" value={`${data.h1_count} found`} status={data.h1_count === 1 ? 'good' : 'bad'} />
                        <MetaItem label="Open Graph" value={data.has_open_graph ? 'Present' : 'Missing'} status={data.has_open_graph ? 'good' : 'warn'} />
                        <MetaItem label="Schema Markup" value={data.has_schema_markup ? 'Present' : 'Missing'} status={data.has_schema_markup ? 'good' : 'warn'} />
                    </div>

                    {(data.issues.length > 0 || data.recommendations.length > 0) && (
                        <div className="space-y-4">
                            {data.issues.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-bold text-muted uppercase tracking-wider mb-2">Issues ({data.issues.length})</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {data.issues.map((issue, i) => (
                                            <span key={i} className="px-3 py-1 rounded-full bg-red/10 text-red border border-red/20 text-xs font-medium">
                                                {issue}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {data.recommendations.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-bold text-muted uppercase tracking-wider mb-2">Recommendations</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {data.recommendations.map((rec, i) => (
                                            <span key={i} className="px-3 py-1 rounded-full bg-green/10 text-green-light border border-green/20 text-xs font-medium">
                                                {rec}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function MetaItem({ label, value, status, truncate }: { label: string, value: string, status: 'good' | 'warn' | 'bad', truncate?: boolean }) {
    const colors = {
        good: 'text-green',
        warn: 'text-yellow',
        bad: 'text-red'
    };

    return (
        <div className="bg-surface p-4 rounded-lg border border-border/50">
            <div className="text-xs text-muted uppercase tracking-wider mb-1">{label}</div>
            <div className={`font-semibold ${colors[status]} ${truncate ? 'truncate' : ''}`} title={value}>
                {value}
            </div>
        </div>
    );
}
