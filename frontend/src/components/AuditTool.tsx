'use client';

import { useState } from 'react';
import { api, type AuditResult } from '@/lib/api';
import { CheckCircle, AlertTriangle, XCircle, Search } from 'lucide-react';

export default function AuditTool() {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<AuditResult | null>(null);
    const [error, setError] = useState('');

    const audit = async () => {
        if (!url) return;
        setLoading(true);
        setError('');
        setData(null);
        try {
            const res = await api.auditSite(url);
            setData(res);
        } catch (err: any) {
            setError(err.message || 'Audit failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-card border border-border rounded-xl p-8 shadow-2xl">
            <div className="flex gap-4 mb-8">
                <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && audit()}
                    placeholder="https://example.com"
                    className="flex-1 bg-surface border border-border rounded-lg px-4 py-3 text-foreground focus:border-green outline-none transition-colors placeholder:text-muted"
                />
                <button
                    onClick={audit}
                    disabled={loading}
                    className="bg-green text-background font-bold px-8 py-3 rounded-lg hover:bg-green-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {loading ? <div className="w-5 h-5 border-2 border-background border-t-transparent rounded-full animate-spin" /> : 'Run Audit'}
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
                            <div className={`text-5xl font-black mb-1 ${data.health_score >= 80 ? 'text-green' : data.health_score >= 50 ? 'text-yellow' : 'text-red'}`}>
                                {data.health_score}
                            </div>
                            <div className="text-xs text-muted uppercase tracking-wider">Health Score</div>
                        </div>
                        <div className="h-16 w-px bg-border/50" />
                        <div>
                            <h2 className="text-xl font-bold mb-2 truncate max-w-md">{data.url}</h2>
                            <div className="flex gap-4 text-sm text-muted">
                                <span className="flex items-center gap-1 text-green">
                                    <CheckCircle size={14} /> {data.passed} passed
                                </span>
                                <span className="flex items-center gap-1 text-yellow">
                                    <AlertTriangle size={14} /> {data.warnings} warnings
                                </span>
                                <span className="flex items-center gap-1 text-red">
                                    <XCircle size={14} /> {data.issues_count} issues
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-3">
                        {data.checks.issues.map((item, i) => (
                            <AuditItem key={`issue-${i}`} type="error" check={item.check} detail={item.detail} />
                        ))}
                        {data.checks.warnings.map((item, i) => (
                            <AuditItem key={`warn-${i}`} type="warn" check={item.check} detail={item.detail} />
                        ))}
                        {data.checks.passed.map((item, i) => (
                            <AuditItem key={`pass-${i}`} type="pass" check={item.check} detail={item.detail} />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function AuditItem({ type, check, detail }: { type: 'error' | 'warn' | 'pass', check: string, detail: string }) {
    const icons = {
        error: <XCircle className="text-red shrink-0" size={18} />,
        warn: <AlertTriangle className="text-yellow shrink-0" size={18} />,
        pass: <CheckCircle className="text-green shrink-0" size={18} />
    };

    return (
        <div className="flex items-start gap-4 p-4 bg-surface border border-border/50 rounded-lg">
            {icons[type]}
            <div>
                <div className="font-semibold text-foreground text-sm">{check}</div>
                <div className="text-muted text-xs mt-0.5">{detail}</div>
            </div>
        </div>
    );
}
