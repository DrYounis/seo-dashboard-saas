import Link from 'next/link';

export default function Navbar() {
    return (
        <nav className="glass-nav sticky top-0 z-50 border-b border-border px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2 text-green-light font-bold text-lg">
                <span>📊</span> SEO Dashboard
            </div>

            <div className="flex items-center gap-6">
                <Link href="#pricing" className="text-sm text-muted hover:text-foreground transition-colors">Pricing</Link>
                <Link href="/docs" target="_blank" className="text-sm text-muted hover:text-foreground transition-colors">API</Link>
                <button className="bg-green text-background font-semibold py-2 px-5 rounded-lg text-sm hover:-translate-y-0.5 transition-all shadow-lg shadow-green/20">
                    Get Started
                </button>
            </div>
        </nav>
    );
}
