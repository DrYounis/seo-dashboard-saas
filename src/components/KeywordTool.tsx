'use client';

import { useState } from 'react';
import { api, type KeywordData } from '@/lib/api';
import { Search, TrendingUp, BarChart2, DollarSign, Target } from 'lucide-react';

export default function KeywordTool({ apiKey }: { apiKey: string }) {
    const [keyword, setKeyword] = useState('');
    const [country, setCountry] = useState('us');
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<KeywordData | null>(null);
    const [error, setError] = useState('');

    const research = async () => {
        if (!keyword) return;
        setLoading(true);
        setError('');
        setData(null);
        try {
            const res = await api.researchKeywords(apiKey, keyword);
            setData(res);
        } catch (err: any) {
            setError(err.message || 'Research failed');
        } finally {
            setLoading(false);
        }
    };

    const getDifficultyColor = (score: number) => {
        if (score < 35) return 'text-green';
        if (score < 60) return 'text-yellow';
        return 'text-red';
    };

    return (
        <div className="bg-card border border-border rounded-xl p-8 shadow-2xl">
            <div className="flex gap-4 mb-8">
                <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && research()}
                    placeholder="Enter keyword (e.g. ai automation)"
                    className="flex-1 bg-surface border border-border rounded-lg px-4 py-3 text-foreground focus:border-green outline-none transition-colors placeholder:text-muted"
                />
                <select
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className="bg-surface border border-border rounded-lg px-4 py-3 text-foreground focus:border-green outline-none transition-colors cursor-pointer"
                >
                    <option value="us">🇺🇸 US</option>
                    <option value="sa">🇸🇦 SA</option>
                    <option value="gb">🇬🇧 GB</option>
                    <option value="ae">🇦🇪 AE</option>
                </select>
                <button
                    onClick={research}
                    disabled={loading}
                    className="bg-green text-background font-bold px-8 py-3 rounded-lg hover:bg-green-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {loading ? <div className="w-5 h-5 border-2 border-background border-t-transparent rounded-full animate-spin" /> : 'Research'}
                </button>
            </div>

            {error && (
                <div className="bg-red/10 border border-red/20 text-red p-4 rounded-lg mb-6">
                    {error}
                </div>
            )}

            {data && (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                        <StatCard
                            label="Monthly Volume"
                            value={data.monthly_volume.toLocaleString()}
                            icon={<BarChart2 size={20} className="text-muted" />}
                        />
                        <StatCard
                            label="Keyword Difficulty"
                            value={`${data.difficulty}/100`}
                            className={getDifficultyColor(data.difficulty)}
                            icon={<Target size={20} className="text-muted" />}
                        />
                        <StatCard
                            label="CPC (USD)"
                            value={`$${data.cpc_usd}`}
                            icon={<DollarSign size={20} className="text-muted" />}
                        />
                    </div>

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        <MetaCard label="Competition" value={data.competition} />
                        <MetaCard label="Opportunity" value={`${100 - data.difficulty}/100`} className="text-green" />
                        <MetaCard label="Trend" value="Stable" />
                        <MetaCard label="Related" value={data.related_keywords.length} size="sm" />
                    </div>

                    <div>
                        <h3 className="text-sm font-bold text-muted uppercase tracking-wider mb-4">Related Keywords</h3>
                        <div className="bg-surface border border-border rounded-xl overflow-hidden">
                            {data.related_keywords.map((k, i) => (
                                <div key={i} className="flex justify-between items-center p-4 border-b border-border/50 last:border-0 hover:bg-white/5 transition-colors">
                                    <span className="font-medium text-foreground">{k.keyword}</span>
                                    <div className="flex gap-6 text-sm text-muted">
                                        <span>{k.volume.toLocaleString()} vol</span>
                                        <span>KD {k.difficulty}</span>
                                        <span>${k.cpc}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function StatCard({ label, value, icon, className = '' }: any) {
    return (
        <div className="bg-surface p-6 rounded-xl border border-border flex flex-col items-center justify-center text-center">
            <div className={`text-3xl font-black mb-1 ${className}`}>{value}</div>
            <div className="text-sm text-muted flex items-center gap-2">
                {icon} {label}
            </div>
        </div>
    );
}

function MetaCard({ label, value, className = '', size = 'md' }: any) {
    return (
        <div className="bg-surface p-4 rounded-lg border border-border/50">
            <div className="text-xs text-muted uppercase tracking-wider mb-1">{label}</div>
            <div className={`font-semibold ${className} ${size === 'sm' ? 'text-sm truncate' : ''}`} title={String(value)}>
                {value}
            </div>
        </div>
    );
}
