const API_BASE = 'http://localhost:8002';

export interface DomainAnalysis {
    domain: string;
    seo_score: number;
    status_code: number;
    load_time_seconds: number;
    has_ssl: boolean;
    title: string;
    title_length: number;
    meta_description: string;
    h1_count: number;
    has_canonical: boolean;
    has_open_graph: boolean;
    has_schema_markup: boolean;
    word_count: number;
    issues: string[];
    recommendations: string[];
}

export interface KeywordData {
    keyword: string;
    monthly_volume: number;
    keyword_difficulty: number;
    cpc_usd: number;
    competition: string;
    trend: string;
    opportunity_score: number;
    serp_features: string[];
    related_keywords: {
        keyword: string;
        volume: number;
        difficulty: number;
        cpc: number;
    }[];
}

export interface AuditResult {
    url: string;
    health_score: number;
    passed: number;
    warnings: number;
    issues_count: number;
    checks: {
        passed: { check: string; detail: string }[];
        warnings: { check: string; detail: string }[];
        issues: { check: string; detail: string }[];
    };
}

export const api = {
    analyzeDomain: async (domain: string, apiKey?: string): Promise<DomainAnalysis> => {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (apiKey) headers['X-API-Key'] = apiKey;
        const res = await fetch(`${API_BASE}/domain`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ domain }),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Analysis failed');
        }
        return res.json();
    },

    researchKeyword: async (keyword: string, country: string = 'us', apiKey?: string): Promise<KeywordData> => {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (apiKey) headers['X-API-Key'] = apiKey;
        const res = await fetch(`${API_BASE}/keywords`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ keyword, country }),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Research failed');
        }
        return res.json();
    },

    auditSite: async (url: string, apiKey?: string): Promise<AuditResult> => {
        const headers: HeadersInit = { 'Content-Type': 'application/json' };
        if (apiKey) headers['X-API-Key'] = apiKey;
        const res = await fetch(`${API_BASE}/audit`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ url }),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Audit failed');
        }
        return res.json();
    },

    checkout: async (plan: string, email: string): Promise<{ checkout_url: string }> => {
        const res = await fetch(`${API_BASE}/checkout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan, email }),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Checkout failed');
        }
        return res.json();
    }
};
