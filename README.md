# MasterTools Domains — .GY Domain Marketplace & Registrar Platform

MasterTools Domains is a modern, developer-first domain marketplace built exclusively for the **`.gy`** country-code top-level domain (ccTLD), administered by the University of Guyana .GY Registry.

Customers can search `.gy` domain names, verify registry availability, submit manual registration requests with unique tracking IDs, and configure 1-click Cloudflare Anycast DNS bridging directly to **Vercel** and **Render**.

---

## 🏛️ Architecture Overview

```
                      MASTERTOOLS DOMAINS
                               │
                        Enter your name
                            [ tala ]
                               │
                            Search
                               │
                            tala.gy
                               │
                      Check availability
             (University of Guyana .GY Registry)
                               │
                      Choose registration
                  (Accredited .GY Registrar)
                               │
                      Connect your website
                    (Cloudflare Anycast DNS)
                         /          \
                      Vercel       Render
```

---

## 🚀 Key Features

- **Exclusive `.gy` ccTLD Focus**: Search and discover names ending strictly in `.gy` (e.g. `tala.gy`, `prem.gy`, `mastertools.gy`, `myshop.gy`).
- **Manual Registration Request Workflow**:
  - Customers can submit registration inquiries with their name, email, domain, and project notes.
  - Generates unique tracking IDs (`REQ-GY-XXXXXXXX`) with instant confirmation.
  - Built-in deduplication blocks active duplicate requests for the same domain (HTTP 409 Conflict).
  - Clear compliance disclosures stating requests do not automatically register or reserve names until confirmed with accredited registrars.
- **Internal Admin Operations Portal**:
  - Overview KPI metrics (Total Requests, Pending Review, Verified Available, In Progress, Registered).
  - Filter requests by status and search by domain, customer name, email, or request ID.
  - Workflow status management:
    - `pending`
    - `verification_required`
    - `verified_available`
    - `unavailable`
    - `registration_in_progress`
    - `registered`
    - `rejected`
  - Internal admin notes and confirmed registrar pricing inputs.
- **Cloudflare Anycast DNS Bridge**:
  - Automated DNS zone file presets for Vercel and Render with instant Let's Encrypt SSL.
- **Registrar Provider Abstraction**:
  - Modular provider architecture ready for live registry/accredited registrar APIs (`BaseRegistrarProvider`, `MockRegistrarProvider`, `GoDaddyRegistrarProvider`, `NamecheapRegistrarProvider`).

---

## 🛠️ Tech Stack

- **Frontend**:
  - React 19 + TypeScript
  - Vite
  - Tailwind CSS
  - Lucide React
- **Backend**:
  - FastAPI (Python 3.13)
  - Pydantic v2
  - Uvicorn
  - Persistent SQLite storage (`backend/data/registrations.db`)
  - Pytest test suite

---

## 📦 Project Structure

```
mastertools-domains/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── domains.py           # Domain search & extension endpoints
│   │   │   └── registrations.py     # Customer & Admin registration request API
│   │   ├── core/
│   │   │   └── config.py            # Environment & registrar provider settings
│   │   ├── models/
│   │   │   ├── domain.py            # Domain & pricing schemas
│   │   │   ├── registrar.py         # Registrar provider schemas
│   │   │   └── registration.py      # Registration request & status models
│   │   ├── services/
│   │   │   ├── catalog_service.py   # .GY extension catalog
│   │   │   ├── pricing_service.py   # Pricing calculations
│   │   │   ├── registration_service.py # SQLite persistent request management
│   │   │   ├── search_service.py    # .GY variation generator
│   │   │   ├── validation_service.py# RFC 1035/1123 domain syntax validation
│   │   │   └── registrar/           # Registrar abstraction & provider implementations
│   │   ├── tests/
│   │   │   └── test_registrations.py# Comprehensive pytest suite
│   │   └── main.py                  # FastAPI application entrypoint
│   ├── data/
│   │   └── registrations.db         # Persistent SQLite database
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── domainService.ts     # Frontend API client
│   │   ├── components/
│   │   │   ├── AdminDashboardModal.tsx # Admin & Liaison Operations Portal
│   │   │   ├── CartDrawer.tsx       # .GY registration queue drawer
│   │   │   ├── DeployIntegrations.tsx# Vercel & Render DNS presets
│   │   │   ├── DomainResultCard.tsx # Domain result card with Request CTA
│   │   │   ├── DomainSearchBar.tsx  # .GY search bar
│   │   │   ├── DomainSearchResults.tsx# Filtered search results
│   │   │   ├── FeaturedDeals.tsx    # .GY showcase & ecosystem
│   │   │   ├── FeaturesBenefits.tsx # Platform value propositions
│   │   │   ├── Footer.tsx           # Footer with registry directory links
│   │   │   ├── HeroSection.tsx      # Hero section
│   │   │   ├── HowItWorks.tsx       # 4-step workflow
│   │   │   ├── Navbar.tsx           # Navigation bar with Admin link
│   │   │   ├── PopularExtensions.tsx# Official .GY Registry spotlight
│   │   │   ├── QuickConnectModal.tsx# Cloudflare DNS bridge modal
│   │   │   └── RegistrationRequestModal.tsx # Customer request modal
│   │   ├── types/
│   │   │   └── domain.ts            # TypeScript definitions
│   │   ├── App.tsx                  # Main application container
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## 🏃 Getting Started

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest

# Run tests
PYTHONPATH=. pytest app/tests/test_registrations.py -v

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API Documentation will be available at: `http://localhost:8000/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run lint and build checks
npm run lint
npm run build

# Start Vite dev server
npm run dev -- --host 0.0.0.0
```

The web application will be available at: `http://localhost:5173`

---

## 🔗 Official Registry Information

- **Registry Authority**: University of Guyana .GY Registry
- **Accredited Registrar Directory**: [https://registry.gy/registrars/](https://registry.gy/registrars/)
- **Pricing**: Standard accredited registrar rates (~$45.00 USD/year)
- **Policy**: Registration requests submitted on MasterTools are coordinated manually with authorized accredited registrars.
