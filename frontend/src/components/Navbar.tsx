import React, { useState } from 'react';
import { Globe, ShoppingCart, Menu, X, Server, ExternalLink, ShieldCheck } from 'lucide-react';
import type { BackendStatus } from '../api/domainService';

interface NavbarProps {
  backendStatus: BackendStatus;
  cartCount: number;
  onOpenCart: () => void;
  onOpenAdmin?: () => void;
  onSelectNav: (sectionId: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  backendStatus,
  cartCount,
  onOpenCart,
  onOpenAdmin,
  onSelectNav,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollTo = (id: string) => {
    setMobileMenuOpen(false);
    onSelectNav(id);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-[#07090e]/85 backdrop-blur-md transition-all">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand / Logo */}
        <div className="flex items-center gap-8">
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="group flex items-center gap-2.5 transition-opacity hover:opacity-95"
          >
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-600 to-indigo-600 shadow-lg shadow-emerald-500/25">
              <Globe className="h-5 w-5 text-white transition-transform group-hover:rotate-12" />
              <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-500 opacity-20 blur transition group-hover:opacity-40" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                MasterTools
                <span className="rounded-md bg-emerald-500/20 border border-emerald-500/40 px-1.5 py-0.5 text-[11px] font-mono font-bold text-emerald-300">
                  Domains
                </span>
                <span className="rounded-md bg-amber-500/20 border border-amber-500/30 px-1.5 py-0.5 text-[9px] font-mono font-bold text-amber-300">
                  FREE TEST
                </span>
              </span>
              <span className="text-[11px] text-slate-400 font-medium -mt-1">
                Multi-TLD Testing (.gy, .com, .in...)
              </span>
            </div>
          </a>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-slate-300">
            <button
              onClick={() => scrollTo('search-section')}
              className="rounded-lg px-3 py-1.5 transition-colors hover:text-white hover:bg-slate-800/60"
            >
              Search
            </button>
            <button
              onClick={() => scrollTo('extensions-section')}
              className="rounded-lg px-3 py-1.5 transition-colors hover:text-white hover:bg-slate-800/60"
            >
              Extensions & Catalog
            </button>
            <button
              onClick={() => scrollTo('deploy-integrations')}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition-colors hover:text-white hover:bg-slate-800/60"
            >
              <Server className="h-3.5 w-3.5 text-blue-400" />
              Vercel & Render
            </button>
            <button
              onClick={() => scrollTo('how-it-works')}
              className="rounded-lg px-3 py-1.5 transition-colors hover:text-white hover:bg-slate-800/60"
            >
              How It Works
            </button>
            <button
              onClick={() => scrollTo('featured-deals')}
              className="rounded-lg px-3 py-1.5 transition-colors hover:text-white hover:bg-slate-800/60 text-emerald-300"
            >
              Showcase
            </button>
            <button
              onClick={() => scrollTo('features-section')}
              className="rounded-lg px-3 py-1.5 transition-colors hover:text-white hover:bg-slate-800/60"
            >
              Features
            </button>
          </nav>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {/* Official Registry Directory Link */}
          <a
            href="https://registry.gy/registrars/"
            target="_blank"
            rel="noopener noreferrer"
            title="View accredited .GY registrars at registry.gy"
            className="hidden xl:inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-950/20 px-2.5 py-1 text-[11px] font-medium text-emerald-300 hover:bg-emerald-900/30 transition-colors"
          >
            <span>.GY Registrars</span>
            <ExternalLink className="h-3 w-3" />
          </a>

          {/* Backend Status indicator */}
          <div
            title={backendStatus.message || (backendStatus.connected ? 'FastAPI API Connected' : 'Mock Mode')}
            className="hidden lg:flex items-center gap-1.5 rounded-full border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-xs text-slate-400"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus.connected
                  ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse'
                  : 'bg-amber-400'
              }`}
            />
            <span className="font-mono text-[11px]">
              {backendStatus.connected ? 'API Connected' : 'Mock Ready'}
            </span>
          </div>

          {/* Admin Portal Button */}
          {onOpenAdmin && (
            <button
              type="button"
              onClick={onOpenAdmin}
              title="Open Registry Operations & Admin Portal"
              className="hidden lg:flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-950/30 px-3 py-1.5 text-xs font-semibold text-indigo-300 hover:bg-indigo-900/40 hover:text-white transition-all cursor-pointer"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
              <span>Admin Portal</span>
            </button>
          )}

          {/* Cart Button */}
          <button
            type="button"
            onClick={onOpenCart}
            aria-label="View Selected Domains"
            className="relative flex h-9.5 items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-900/90 px-3 py-1.5 text-sm font-medium text-slate-200 transition-all hover:border-slate-600 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/40 cursor-pointer"
          >
            <ShoppingCart className="h-4 w-4 text-slate-300" />
            <span className="hidden sm:inline">Selected</span>
            {cartCount > 0 ? (
              <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-gradient-to-r from-emerald-600 to-teal-600 px-1.5 text-xs font-bold text-white shadow-sm">
                {cartCount}
              </span>
            ) : (
              <span className="text-xs text-slate-500">0</span>
            )}
          </button>

          {/* Search CTA */}
          <button
            type="button"
            onClick={() => scrollTo('search-section')}
            className="relative inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-emerald-600/20 transition-all hover:brightness-110 active:scale-[0.98] cursor-pointer"
          >
            Search Free ($0)
          </button>

          {/* Mobile menu toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden flex h-9.5 w-9.5 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:text-white"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-slate-800 bg-[#0a0f1d] px-4 py-4 space-y-2">
          <button
            onClick={() => scrollTo('search-section')}
            className="block w-full text-left rounded-md px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            .GY Domain Search
          </button>
          <button
            onClick={() => scrollTo('extensions-section')}
            className="block w-full text-left rounded-md px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            Registry & Accreditation Info
          </button>
          <button
            onClick={() => scrollTo('deploy-integrations')}
            className="block w-full text-left rounded-md px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            Vercel & Render Connection
          </button>
          <button
            onClick={() => scrollTo('how-it-works')}
            className="block w-full text-left rounded-md px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            How It Works
          </button>
          <button
            onClick={() => scrollTo('featured-deals')}
            className="block w-full text-left rounded-md px-3 py-2 text-sm font-medium text-emerald-300 hover:bg-slate-800"
          >
            .GY Showcase & Use Cases
          </button>
          <button
            onClick={() => scrollTo('features-section')}
            className="block w-full text-left rounded-md px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
          >
            Features & Benefits
          </button>
          {onOpenAdmin && (
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                onOpenAdmin();
              }}
              className="flex items-center gap-2 w-full text-left rounded-md px-3 py-2 text-sm font-semibold text-indigo-300 bg-indigo-950/40 border border-indigo-500/30 hover:bg-indigo-900/50"
            >
              <ShieldCheck className="h-4 w-4 text-indigo-400" />
              <span>Admin & Liaison Operations Portal</span>
            </button>
          )}
          <div className="pt-2 border-t border-slate-800">
            <a
              href="https://registry.gy/registrars/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-1.5 w-full rounded-lg border border-emerald-500/40 bg-emerald-950/30 py-2 text-xs font-semibold text-emerald-300"
            >
              <span>View Accredited .GY Registrars</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      )}
    </header>
  );
};
