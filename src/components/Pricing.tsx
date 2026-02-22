'use client';

import { useState } from 'react';
import { SUBSCRIPTION_PLANS } from '@/lib/pricing';
import { api } from '@/lib/api';
import { Check } from 'lucide-react';

export default function Pricing() {
    const [loading, setLoading] = useState<string | null>(null);

    const handleCheckout = async (planId: string) => {
        setLoading(planId);
        try {
            // TODO: Get real email from auth
            const result = await api.checkout(planId, 'user@example.com');
            if (result.checkout_url) {
                window.location.href = result.checkout_url;
            }
        } catch (err) {
            console.error('Checkout failed:', err);
        } finally {
            setLoading(null);
        }
    };

    return (
        <section id="pricing" className="py-24 px-6 md:px-12 bg-background/50">
            <div className="max-w-7xl mx-auto">
                <div className="text-center mb-16">
                    <h2 className="text-4xl md:text-5xl font-black mb-6">Simple, Transparent Pricing</h2>
                    <p className="text-muted text-xl max-w-2xl mx-auto">
                        Choose the plan that fits your growth. No hidden fees. Cancel anytime.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {SUBSCRIPTION_PLANS.map((plan) => (
                        <div key={plan.id} className={`relative p-8 rounded-2xl border ${plan.name === 'Pro' ? 'bg-surface/50 border-green shadow-2xl shadow-green/10' : 'bg-surface border-border'} flex flex-col`}>
                            {plan.name === 'Pro' && (
                                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-green text-background text-sm font-bold px-4 py-1 rounded-full uppercase tracking-wide">
                                    Most Popular
                                </div>
                            )}
                            <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
                            <div className="flex items-baseline gap-1 mb-6">
                                <span className="text-4xl font-black">${plan.price}</span>
                                <span className="text-muted">/{plan.interval}</span>
                            </div>
                            <div className="flex-1 space-y-4 mb-8">
                                {plan.features.map((feature, i) => (
                                    <div key={i} className="flex items-start gap-3 text-sm text-muted">
                                        <Check className="text-green shrink-0" size={18} />
                                        <span>{feature}</span>
                                    </div>
                                ))}
                            </div>
                            <button
                                onClick={() => handleCheckout(plan.id)}
                                disabled={loading === plan.id}
                                className={`w-full py-3 rounded-xl font-bold transition-all duration-200 ${plan.name === 'Pro'
                                    ? 'bg-green text-background hover:bg-green-light shadow-lg shadow-green/20'
                                    : 'bg-white/10 text-foreground hover:bg-white/20'
                                    }`}
                            >
                                {loading === plan.id ? 'Loading...' : `Get ${plan.name}`}
                            </button>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
