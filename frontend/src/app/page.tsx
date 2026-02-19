'use client';

import { useState } from 'react';
import Navbar from '@/components/Navbar';
import DomainTool from '@/components/DomainTool';
import KeywordTool from '@/components/KeywordTool';
import AuditTool from '@/components/AuditTool';
import Pricing from '@/components/Pricing';
import { Globe, Search, Shield } from 'lucide-react';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'domain' | 'keywords' | 'audit'>('domain');

  return (
    <main className="min-h-screen bg-background text-foreground font-sans selection:bg-green/20 selection:text-green">
      <Navbar />

      <section className="hero-gradient pt-24 pb-12 px-6 text-center">
        <div className="inline-flex items-center gap-2 bg-green/10 border border-green/20 rounded-full px-4 py-1 text-sm text-green-light font-medium mb-6 animate-in fade-in zoom-in duration-500">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green"></span>
          </span>
          AI-Powered SEO Intelligence
        </div>

        <h1 className="text-5xl md:text-7xl font-black mb-6 tracking-tight">
          SEO Analysis That<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-green-light to-cyan">Actually Drives Results</span>
        </h1>

        <p className="text-muted text-xl max-w-2xl mx-auto mb-12 leading-relaxed">
          Domain overview, keyword research, and site audits — all in one dashboard.
          Get actionable insights in seconds without the enterprise price tag.
        </p>

        <div className="flex flex-wrap justify-center gap-4 mb-12">
          <TabButton
            active={activeTab === 'domain'}
            onClick={() => setActiveTab('domain')}
            icon={<Globe size={18} />}
            label="Domain Overview"
          />
          <TabButton
            active={activeTab === 'keywords'}
            onClick={() => setActiveTab('keywords')}
            icon={<Search size={18} />}
            label="Keyword Research"
          />
          <TabButton
            active={activeTab === 'audit'}
            onClick={() => setActiveTab('audit')}
            icon={<Shield size={18} />}
            label="Site Audit"
          />
        </div>

        <div className="max-w-4xl mx-auto min-h-[400px]">
          {activeTab === 'domain' && <DomainTool />}
          {activeTab === 'keywords' && <KeywordTool />}
          {activeTab === 'audit' && <AuditTool />}
        </div>
      </section>

      <Pricing />

      <footer className="border-t border-border py-8 text-center text-sm text-muted">
        <p>© 2026 SEO Dashboard · AI-Powered SEO Intelligence · <a href="/docs" className="text-green-light hover:underline">API Docs</a></p>
      </footer>
    </main>
  );
}

function TabButton({ active, onClick, icon, label }: any) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-6 py-3 rounded-lg font-bold transition-all duration-200 ${active
          ? 'bg-green text-background shadow-lg shadow-green/20 translate-y-0'
          : 'bg-transparent border border-border text-muted hover:bg-white/5 hover:text-foreground hover:-translate-y-0.5'
        }`}
    >
      {icon} {label}
    </button>
  );
}
