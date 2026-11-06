import React from 'react';
import { Sparkles, ArrowRight } from 'lucide-react';
import { FEATURED_DEALS } from '../data/extensionCatalog';
import type { FeaturedDeal } from '../types/domain';

interface FeaturedDealsProps {
  onClaimDeal: (deal: FeaturedDeal) => void;
}

export const FeaturedDeals: React.FC<FeaturedDealsProps> = ({ onClaimDeal }) => {
  return (
    <section id="featured-deals" className="w-full py-12 relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-emerald-600/10 blur-[120px] pointer-events-none rounded-full" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Multi-Extension Showcase</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Featured Domain Use Cases (<span className="text-emerald-400 font-mono">Free Testing</span>)
            </h2>
          </div>
          <p className="text-sm text-slate-400 max-w-md">
            Memorable names for creators, startups, enterprises, and platforms. Free application testing with instant Vercel and Render DNS presets.
          </p>
        </div>

        {/* Deals Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {FEATURED_DEALS.map((deal) => {
            return (
              <div
                key={deal.id}
                className="group relative flex flex-col justify-between rounded-2xl border border-slate-800 bg-[#0c1222]/90 p-5 transition-all duration-300 hover:border-emerald-500/50 hover:bg-[#101b2e] hover:shadow-xl hover:shadow-emerald-950/30"
              >
                {/* Top Badge */}
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      deal.badgeColor === 'purple'
                        ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                        : deal.badgeColor === 'amber'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : deal.badgeColor === 'blue'
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }`}
                  >
                    {deal.badge}
                  </span>
                  <span className="text-[11px] text-emerald-400 font-mono font-bold">
                    $0 / Free
                  </span>
                </div>

                {/* Sample Domain & Headline */}
                <div className="space-y-1.5 mb-4">
                  <div className="text-2xl sm:text-3xl font-extrabold font-mono tracking-tight text-white group-hover:text-emerald-300 transition-colors">
                    {deal.sampleDomain}
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200">
                    {deal.headline}
                  </h3>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {deal.description}
                  </p>
                </div>

                {/* Pricing & CTA */}
                <div className="pt-3 border-t border-slate-800/80">
                  <div className="flex items-baseline justify-between mb-3">
                    <div>
                      <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-extrabold text-emerald-400 font-mono">
                          FREE
                        </span>
                        <span className="text-xs text-slate-400">($0 Testing)</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        No payment required
                      </div>
                    </div>
                    <span className="rounded-lg bg-emerald-500/15 border border-emerald-500/30 px-2 py-1 text-[11px] font-semibold text-emerald-300">
                      Testing Mode
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => onClaimDeal(deal)}
                    className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-slate-900 border border-slate-700/80 py-2.5 text-xs font-semibold text-slate-200 group-hover:bg-gradient-to-r group-hover:from-emerald-600 group-hover:to-teal-600 group-hover:border-transparent group-hover:text-white transition-all shadow-sm cursor-pointer"
                  >
                    <span>Search {deal.sampleDomain}</span>
                    <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
