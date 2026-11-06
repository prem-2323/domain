import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Sparkles,
  Shield,
  Lock,
  Server,
  AlertCircle,
  Send,
} from 'lucide-react';
import type { DomainSearchResult } from '../types/domain';

interface DomainResultCardProps {
  item: DomainSearchResult;
  isInCart?: boolean;
  onAddToCart?: (item: DomainSearchResult) => void;
  onOpenQuickConnect: (item: DomainSearchResult) => void;
  onRequestRegistration?: (item: DomainSearchResult) => void;
  isHeroMatch?: boolean;
}

export const DomainResultCard: React.FC<DomainResultCardProps> = ({
  item,
  onAddToCart,
  onOpenQuickConnect,
  onRequestRegistration,
  isHeroMatch = false,
}) => {
  const isAvailable = item.status === 'available';
  const isUnverified = item.status === 'unverified';
  const isPremium = item.status === 'premium';
  const isTaken = item.status === 'taken';

  const handleRequestClick = () => {
    if (onRequestRegistration) {
      onRequestRegistration(item);
    } else if (onAddToCart) {
      onAddToCart(item);
    }
  };

  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border transition-all duration-200 ${
        isHeroMatch
          ? isTaken
            ? 'border-slate-700 bg-[#0d1424] p-5 sm:p-6'
            : 'border-emerald-500/60 bg-gradient-to-r from-[#0a1e1b] via-[#0b1626] to-[#0c1222] p-5 sm:p-6 shadow-xl shadow-emerald-950/30 ring-1 ring-emerald-500/40'
          : isTaken
          ? 'border-slate-800/60 bg-[#0a0f1d]/50 opacity-80 p-4 sm:p-5'
          : 'border-slate-800 bg-[#0b1120]/80 hover:border-slate-700 hover:bg-[#0e172c] p-4 sm:p-5'
      }`}
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left Side: Domain details & Badges */}
        <div className="space-y-2">
          {isHeroMatch && (
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-[10px] font-bold text-emerald-300 uppercase tracking-wider">
                Exact Search Match
              </span>
              <span className="text-[11px] text-slate-400">
                .GY ccTLD Registry • Live Partner Verification Required
              </span>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-mono flex items-baseline">
              <span>{item.name}</span>
              <span
                className={
                  isTaken
                    ? 'text-slate-400'
                    : isAvailable
                    ? 'text-emerald-400 font-extrabold'
                    : 'text-emerald-400 font-extrabold'
                }
              >
                {item.tld}
              </span>
            </h3>

            {/* Status Badge */}
            {isUnverified && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2.5 py-0.5 text-xs font-semibold text-amber-300">
                <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                Unverified (Registrar Check Required)
              </span>
            )}
            {isAvailable && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                Available (Free for Testing)
              </span>
            )}
            {isPremium && (
              <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/15 border border-purple-500/30 px-2.5 py-0.5 text-xs font-semibold text-purple-300">
                <Sparkles className="h-3.5 w-3.5 text-purple-400" />
                Featured {item.tld}
              </span>
            )}
            {isTaken && (
              <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 border border-rose-500/30 px-2.5 py-0.5 text-xs font-semibold text-rose-400">
                <XCircle className="h-3.5 w-3.5 text-rose-400" />
                Unavailable / Reserved
              </span>
            )}

            {/* Registry Tag */}
            <span className="text-[10px] text-slate-400 font-mono">
              [{item.registry || 'Accredited Registry'}]
            </span>
          </div>

          {/* Value inclusions */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
            <span className="flex items-center gap-1 text-slate-300">
              <Shield className="h-3.5 w-3.5 text-emerald-400" />
              Free WHOIS Privacy
            </span>
            <span className="flex items-center gap-1 text-slate-300">
              <Lock className="h-3.5 w-3.5 text-blue-400" />
              Free SSL Certificate
            </span>
            <span className="flex items-center gap-1 text-slate-300">
              <Server className="h-3.5 w-3.5 text-purple-400" />
              Cloudflare Anycast DNS (Vercel & Render)
            </span>
          </div>
        </div>

        {/* Right Side: Pricing & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between lg:justify-end gap-4 border-t lg:border-t-0 border-slate-800/80 pt-3 lg:pt-0">
          {/* Price breakdown */}
          <div className="text-left sm:text-right">
            {!isTaken ? (
              <>
                <div className="flex items-baseline sm:justify-end gap-1.5">
                  <span className="text-2xl sm:text-3xl font-extrabold text-emerald-400 font-mono">
                    FREE
                  </span>
                  <span className="text-xs text-slate-400">($0 Testing)</span>
                </div>
                <div className="flex items-center sm:justify-end gap-2 text-xs text-emerald-400/80">
                  <span>Free Application Testing</span>
                </div>
              </>
            ) : (
              <div className="text-sm font-medium text-slate-400">
                Reserved or Registered
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {!isTaken ? (
              <>
                {/* 1-click Quick Connect preview */}
                <button
                  type="button"
                  onClick={() => onOpenQuickConnect(item)}
                  title="Configure instant DNS records for Vercel or Render"
                  className="hidden sm:inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2.5 text-xs font-semibold text-slate-200 transition-all hover:border-indigo-500 hover:text-white hover:bg-slate-800"
                >
                  <Server className="h-3.5 w-3.5 text-blue-400" />
                  <span>Connect DNS</span>
                </button>

                {/* Request Registration button */}
                <button
                  type="button"
                  onClick={handleRequestClick}
                  className="flex items-center justify-center gap-2 rounded-xl px-4 sm:px-5 py-2.5 text-xs sm:text-sm font-semibold transition-all shadow-md bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 hover:brightness-110 text-white shadow-emerald-600/25 active:scale-95 cursor-pointer"
                >
                  <Send className="h-4 w-4" />
                  <span>Request Registration</span>
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() =>
                  alert(`WHOIS Query for ${item.domain}: Reserved or registered under the University of Guyana .GY Registry. Contact accredited registrar for brokerage or allocation inquiries.`)
                }
                className="rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
              >
                WHOIS / Registry Info
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
