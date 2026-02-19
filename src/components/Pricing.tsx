'use client';

import { useState } from 'react';
import { Check, X } from 'lucide-react';
import { api } from '@/lib/api';

export default function Pricing() {
    const [selectedPlan, setSelectedPlan] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);

    const plans = [
        {
            name: 'Starter',
            price: '$49',
            desc: 'For solo marketers',
            features: ['10 reports/month', 'Domain overview', 'Keyword research', 'PDF export', 'Email support'],
            highlight: false
        },
        {
            name: 'Professional',
            price: '$149',
            desc: 'For growing businesses',
            features: ['50 reports/month', 'Site audit', 'Competitor analysis', 'API access', 'Priority support'],
            highlight: true
        },
        {
            name: 'Agency',
            price: '$499',
            desc: 'For agencies & teams',
            features: ['Unlimited reports', 'White-label', '10 team seats', 'Custom branding', 'Dedicated support'],
            highlight: false
        }
    ];

    const openModal = (planName: string) => {
        setSelectedPlan(planName);
        setIsModalOpen(true);
    };

    const handleCheckout = async () => {
        if (!email || !email.includes('@')) {
            alert('Please enter a valid email');
            return;
        }
        setLoading(true);
        try {
            const res = await api.checkout(selectedPlan.toLowerCase(), email);
            if (res.checkout_url) {
                window.location.href = res.checkout_url;
            }
        } catch (e: any) {
            alert('Checkout failed: ' + e.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <section id="pricing" className="py-20 px-6">
            <div className="text-center mb-16">
                <h2 className="text-3xl font-black mb-4">Simple Pricing</h2>
                <p className="text-muted text-lg">Start free, scale as you grow</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
                {plans.map((plan, i) => (
                    <div key={i} className={`relative bg-card border ${plan.highlight ? 'border-green scale-105 shadow-2xl shadow-green/10 z-10' : 'border-border'} rounded-2xl p-8 hover:-translate-y-2 transition-all duration-300`}>
                        {plan.highlight && (
                            <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-green text-background text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                                Most Popular
                            </span>
                        )}
                        <div className="text-green-light font-bold mb-2">{plan.name}</div>
                        <div className="text-4xl font-black mb-1">{plan.price}<span className="text-base font-normal text-muted">/mo</span></div>
                        <div className="text-sm text-muted mb-8">{plan.desc}</div>

                        <ul className="space-y-4 mb-8">
                            {plan.features.map((f, j) => (
                                <li key={j} className="flex items-center gap-3 text-sm">
                                    <div className="w-5 h-5 rounded-full bg-green/10 flex items-center justify-center shrink-0">
                                        <Check size={12} className="text-green" />
                                    </div>
                                    {f}
                                </li>
                            ))}
                        </ul>

                        <button
                            onClick={() => openModal(plan.name)}
                            className={`w-full py-3 rounded-xl font-bold transition-all ${plan.highlight ? 'bg-green text-background hover:bg-green-light hover:shadow-lg hover:shadow-green/20' : 'bg-transparent border border-border text-green-light hover:bg-green/5'}`}
                        >
                            Get Started
                        </button>
                    </div>
                ))}
            </div>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
                    <div className="bg-card border border-border rounded-xl p-8 max-w-md w-full shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold">🚀 Start Subscription</h3>
                            <button onClick={() => setIsModalOpen(false)} className="text-muted hover:text-foreground">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="mb-6">
                            <div className="text-sm text-muted mb-2">Selected Plan</div>
                            <div className="text-lg font-bold text-green-light">{selectedPlan}</div>
                        </div>

                        <div className="mb-8">
                            <label className="block text-sm font-medium mb-2">Email Address</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="name@company.com"
                                className="w-full bg-surface border border-border rounded-lg px-4 py-3 outline-none focus:border-green transition-colors"
                            />
                        </div>

                        <div className="flex gap-4 justify-end">
                            <button onClick={() => setIsModalOpen(false)} className="px-6 py-2 text-sm text-muted hover:text-foreground">Cancel</button>
                            <button
                                onClick={handleCheckout}
                                disabled={loading}
                                className="bg-green text-background font-bold px-6 py-2 rounded-lg hover:bg-green-light transition-colors disabled:opacity-50"
                            >
                                {loading ? 'Processing...' : 'Continue to Payment →'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </section>
    );
}
