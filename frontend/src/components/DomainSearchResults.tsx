import React, { useState } from 'react';
import type { DomainSearchResult } from '../types/domain';
import { DomainResultCard } from './DomainResultCard';
import {
  Info,
  Filter,
  Search,
  AlertTriangle,
  XCircle,
  ExternalLink,
} from 'lucide-react';

interface DomainSearchResultsProps {
  results: DomainSearchResult[];
  isLoading: boolean;
  searchQuery: string;
  errorMessage?: string | null;
  cartItems: { domain: string }[];
  onAddToCart: (item: DomainSearchResult) => void;
  onOpenQuickConnect: (item: DomainSearchResult) => void;
  onRequestRegistration?: (item: DomainSearchResult) => void;
  onTrySuggestion?: (name: string) => void;
}

export const DomainSearchResults: React.FC<DomainSearchResultsProps> = ({
  results,
  isLoading,
  searchQuery,
  errorMessage,
  cartItems,
  onAddToCart,
  onOpenQuickConnect,
  onRequestRegistration,
  onTrySuggestion,
}) => {
  const [activeFilter, setActiveFilter] = useState<'all' | 'available' | 'taken'>('all');

  const isInCart = (domain: string) => cartItems.some((item) => item.domain === domain);

  // Filtered results
  const filteredResults = results.filter((item) => {
    if (activeFilter === 'available') return item.status === 'unverified' || item.status === 'available' || item.status === 'premium';
    if (activeFilter === 'taken') return item.status === 'taken';
    return true;
  });

  // 1. Loading Skeleton State
  if (isLoading) {
    return (
      <div className="w-full max-w-5xl mx-auto py-8 px-4 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="h-5 w-48 bg-slate-800/80 rounded animate-pulse" />
          <div className="h-5 w-32 bg-slate-800/60 rounded animate-pulse" />
        </div>
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="rounded-2xl border border-slate-800 bg-[#0d1322]/80 p-5 space-y-3 animate-pulse"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-7 w-52 bg-slate-800 rounded-lg" />
                <div className="h-5 w-20 bg-slate-850 rounded-full" />
              </div>
              <div className="h-8 w-28 bg-slate-800 rounded-xl" />
            </div>
            <div className="h-4 w-72 bg-slate-850 rounded" />
          </div>
        ))}
      </div>
    );
  }

  // 2. Error State (e.g. from FastAPI validation failure)
  if (errorMessage) {
    return (
      <section id="search-results-section" className="w-full max-w-3xl mx-auto py-8 px-4">
        <div className="rounded-2xl border border-rose-500/30 bg-gradient-to-b from-[#1c0d16] to-[#0d0912] p-6 sm:p-8 shadow-xl">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-500/20 border border-rose-500/40 text-rose-400 shrink-0">
              <XCircle className="h-6 w-6" />
            </div>
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-rose-500/20 px-2 py-0.5 text-[10px] font-bold text-rose-300 uppercase tracking-wider">
                  Validation Error
                </span>
                <span className="text-xs text-slate-400 font-mono">FastAPI .GY Domain Engine</span>
              </div>
              <h3 className="text-lg font-bold text-white">
                "{searchQuery}" is not a valid .gy domain name
              </h3>
              <p className="text-sm text-rose-300 leading-relaxed font-medium">
                {errorMessage}
              </p>

              {/* Guidelines */}
              <div className="mt-4 rounded-xl border border-slate-800 bg-[#070b14] p-3 text-xs text-slate-300 space-y-1">
                <div className="font-semibold text-slate-200 mb-1">.GY Domain Standards:</div>
                <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                  <li>Between 1 and 63 alphanumeric characters</li>
                  <li>Can contain hyphens (-) but cannot start or end with a hyphen</li>
                  <li>All names are registered under the official .gy ccTLD</li>
                </ul>
              </div>

              {/* Suggested quick fixes */}
              {onTrySuggestion && (
                <div className="pt-3 flex flex-wrap items-center gap-2">
                  <span className="text-xs text-slate-400">Try instead:</span>
                  {['tala', 'prem', 'mastertools', 'myshop', 'myportfolio'].map((sugg) => (
                    <button
                      key={sugg}
                      type="button"
                      onClick={() => onTrySuggestion(sugg)}
                      className="rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs font-mono text-emerald-300 hover:border-emerald-500 hover:text-white transition-colors cursor-pointer"
                    >
                      {sugg}.gy
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    );
  }

  // 3. Initial Empty State (before search)
  if (!searchQuery && results.length === 0) {
    return (
      <div className="w-full max-w-4xl mx-auto py-12 px-4 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-4">
          <Search className="h-6 w-6" />
        </div>
        <h3 className="text-lg font-semibold text-white">
          Enter a domain name above to check .gy availability
        </h3>
        <p className="mt-1 text-sm text-slate-400 max-w-md mx-auto">
          Search for your brand or personal identity (e.g. "tala", "prem", "mastertools", "myshop"). MasterTools searches exclusively on the .gy ccTLD.
        </p>
      </div>
    );
  }

  // 4. Empty State: No results found for query
  if (results.length === 0) {
    return (
      <div className="w-full max-w-3xl mx-auto py-12 px-4 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 mb-3">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <h3 className="text-base font-semibold text-white">No .gy domain variations found for "{searchQuery}"</h3>
        <p className="mt-1 text-xs text-slate-400">
          Try a shorter name or search without special characters.
        </p>
      </div>
    );
  }

  const exactHeroMatch = results[0];

  return (
    <section id="search-results-section" className="w-full max-w-5xl mx-auto py-6 px-4 sm:px-6">
      {/* Registry Transparency Banner */}
      <div className="mb-6 rounded-xl border border-emerald-500/30 bg-gradient-to-r from-emerald-950/40 via-blue-950/20 to-slate-900/60 p-3 sm:p-4 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div className="flex items-start sm:items-center gap-2 text-emerald-300 font-medium">
            <Info className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5 sm:mt-0" />
            <span>
              <strong>University of Guyana .GY Registry Notice:</strong> Availability is marked unverified until checked with an authorized registrar. Registrations are fulfilled through accredited partners.
            </span>
          </div>
          <a
            href="https://registry.gy/registrars/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-full bg-emerald-500/20 hover:bg-emerald-500/30 px-2.5 py-1 text-[10px] font-mono text-emerald-200 uppercase self-start sm:self-auto shrink-0 transition-colors"
          >
            <span>Accredited Registrars</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>

      {/* Results Header & Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-3 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            .GY Results for <span className="text-emerald-400 font-mono">"{searchQuery}"</span>
            <span className="text-xs font-normal text-slate-400">({results.length} .gy variations generated)</span>
          </h2>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <span className="text-xs text-slate-400 mr-1 flex items-center gap-1">
            <Filter className="h-3 w-3" /> Filter:
          </span>
          <button
            type="button"
            onClick={() => setActiveFilter('all')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all cursor-pointer ${
              activeFilter === 'all'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            All ({results.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter('available')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all cursor-pointer ${
              activeFilter === 'available'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            Unverified / Available
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter('taken')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all cursor-pointer ${
              activeFilter === 'taken'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            Reserved / Unavailable
          </button>
        </div>
      </div>

      {/* Featured / Exact Match Hero Card */}
      {exactHeroMatch && (
        <div className="mb-5">
          <DomainResultCard
            item={exactHeroMatch}
            isInCart={isInCart(exactHeroMatch.domain)}
            onAddToCart={onAddToCart}
            onOpenQuickConnect={onOpenQuickConnect}
            onRequestRegistration={onRequestRegistration}
            isHeroMatch={true}
          />
        </div>
      )}

      {/* Alternative .GY Variations */}
      <div className="space-y-3">
        {filteredResults
          .filter((item) => item.domain !== exactHeroMatch?.domain)
          .map((item) => (
            <DomainResultCard
              key={item.domain}
              item={item}
              isInCart={isInCart(item.domain)}
              onAddToCart={onAddToCart}
              onOpenQuickConnect={onOpenQuickConnect}
              onRequestRegistration={onRequestRegistration}
            />
          ))}

        {filteredResults.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-400">
            No domains match the selected filter. Try selecting "All" above.
          </div>
        )}
      </div>
    </section>
  );
};
