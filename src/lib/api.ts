export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

// Types
export interface DomainAnalysis {
    domain: string;
    seo_score: number;
    title: string;
    title_length: number;
    meta_description: string;
    description_length: number;
    load_time_seconds: number;
    has_ssl: boolean;
    h1_count: number;
    h1_text: string;
    has_canonical: boolean;
    has_open_graph: boolean;
    has_schema_markup: boolean;
    has_robots_meta: boolean;
    word_count: number;
    total_images: number;
    images_missing_alt: number;
    issues: string[];
    recommendations: string[];
    analyzed_at: string;
}

export interface KeywordData {
    keyword: string;
    country: string;
    monthly_volume: number;
    keyword_difficulty: number; // mapped from backend 'keyword_difficulty'
    difficulty: number;         // convenience alias if needed, but backend sends 'keyword_difficulty'
    cpc_usd: number;
    competition: string;
    trend: string;
    serp_features: string[];
    opportunity_score: number;
    related_keywords: Array<{
        keyword: string;
        volume: number;
        difficulty: number;
        cpc: number;
    }>;
    analyzed_at: string;
}

export interface AuditResult {
    url: string;
    health_score: number;
    passed: number;
    warnings: number;
    issues_count: number;
    checks: {
        passed: Array<{ check: string; detail: string }>;
        warnings: Array<{ check: string; detail: string }>;
        issues: Array<{ check: string; detail: string }>;
    };
    audited_at: string;
}

// API Client
export const api = {
    async analyzeDomain(apiKey: string, domain: string) {
        const res = await fetch(`${API_BASE_URL}/domain`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey
            },
            body: JSON.stringify({ domain }),
        });
        if (!res.ok) {
            if (res.status === 401) throw new Error('Invalid API Key');
            if (res.status === 429) throw new Error('Quota Exceeded');
            throw new Error('Analysis failed');
        }
        return res.json();
    },

    async researchKeywords(apiKey: string, keyword: string) {
        const res = await fetch(`${API_BASE_URL}/keywords`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey
            },
            body: JSON.stringify({ keyword }),
        });
        if (!res.ok) throw new Error('Research failed');
        const data = await res.json();
        return {
            ...data,
            difficulty: data.keyword_difficulty
        };
    },

    async auditSite(apiKey: string, url: string) {
        const res = await fetch(`${API_BASE_URL}/audit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey
            },
            body: JSON.stringify({ url }),
        });
        if (!res.ok) throw new Error('Audit failed');
        return res.json();
    },

    async getHistory(apiKey: string) {
        const res = await fetch(`${API_BASE_URL}/history`, {
            headers: { 'x-api-key': apiKey },
        });
        if (!res.ok) throw new Error('Failed to fetch history');
        return res.json();
    },

    async checkout(plan: string, email: string) {
        const res = await fetch(`${API_BASE_URL}/checkout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan, email }),
        });
        if (!res.ok) throw new Error('Checkout failed');
        return res.json();
    }
};
