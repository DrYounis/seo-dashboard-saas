import { loadStripe } from '@stripe/stripe-js';

export const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export const SUBSCRIPTION_PLANS = [
    {
        id: 'price_starter',
        name: 'Starter',
        price: 29,
        interval: 'month',
        features: ['10 Domain Analysis/mo', 'Basic Keyword Research', 'Email Support']
    },
    {
        id: 'price_pro',
        name: 'Pro',
        price: 79,
        interval: 'month',
        features: ['Unlimited Domain Analysis', 'Advanced Keyword Data', 'Site Audits', 'Priority Support']
    },
    {
        id: 'price_agency',
        name: 'Agency',
        price: 199,
        interval: 'month',
        features: ['White Label Reports', 'API Access', 'Dedicated Account Manager']
    }
];
