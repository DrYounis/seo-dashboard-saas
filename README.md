# SEO Dashboard SaaS 📊

> **AI-powered SEO analysis — domain overview, keyword research, site audit**

Analyze any domain for SEO signals, research keywords, and run comprehensive site audits. No external API keys required for core functionality.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

---

## 💰 Pricing

| Plan | Price | Reports/month |
|------|-------|---------------|
| Starter | $49/mo | 10 |
| Professional | $149/mo | 50 |
| Agency | $499/mo | Unlimited |

**Target**: 100 users = **$9,900 MRR**

---

## 🏗️ Architecture

```
seo-dashboard/
├── main.py              ← FastAPI backend (domain, keywords, audit, Stripe)
├── dashboard/
│   └── index.html       ← Premium 3-tool SaaS UI
├── requirements.txt
├── railway.json
├── Procfile
└── .env.example
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/DrYounis/seo-dashboard-saas
cd seo-dashboard-saas
pip install -r requirements.txt

cp .env.example .env
# Add Stripe keys

uvicorn main:app --reload --port 8002
# Open http://localhost:8002
```

---

## 🌐 API Reference

### `POST /domain`
Analyze a domain for SEO signals.

**Body**: `{ "domain": "example.com" }`

**Returns**: SEO score, title, meta, H1, load time, issues, recommendations

### `POST /keywords`
Research a keyword.

**Body**: `{ "keyword": "ai tools", "country": "us" }`

**Returns**: Volume, difficulty, CPC, related keywords, SERP features

### `POST /audit`
Run a site audit.

**Body**: `{ "url": "https://example.com" }`

**Returns**: Health score, passed/warning/issue checks

---

## 📄 License

MIT — built by [DrYounis](https://github.com/DrYounis)
