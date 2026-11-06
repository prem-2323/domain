import React from 'react';
import { Sparkles, ShieldCheck, ArrowRight } from 'lucide-react';
import { FREE_TESTING_DISCLAIMER } from '../data/extensionCatalog';

interface PopularExtensionsProps {
  onSelectExtension: (domainQuery: string) => void;
  selectedTld?: string;
}

export const PopularExtensions: React.FC<PopularExtensionsProps> = ({
  onSelectExtension,
}) => {
  const showcaseDomains = [
    { name: 'tala', domain: 'tala.gy', useCase: 'Personal Identity & Portfolios', badge: 'Creator', tld: '.gy' },
    { name: 'prem', domain: 'prem.com', useCase: 'Global Commercial Names', badge: 'Flagship', tld: '.com' },
    { name: 'mastertools', domain: 'mastertools.in', useCase: 'Cloud & Tech Platforms', badge: 'Enterprise', tld: '.in' },
    { name: 'myshop', domain: 'myshop.org', useCase: 'Communities & Organizations', badge: 'Community', tld: '.org' },
    { name: 'myportfolio', domain: 'myportfolio.net', useCase: 'Developer Showcase & Stacks', badge: 'Developer', tld: '.net' },
  ];

  return (
    <section id="extensions-section" className="w-full py-10">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Free Application Testing Mode</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Search All Extensions (<span className="text-emerald-400 font-mono">.gy, .com, .in, .org, .net</span>)
            </h2>
          </div>
          <p className="text-sm text-slate-400 max-w-lg">
            MasterTools Domains supports multiple TLDs for testing. All domain searches and registration requests are 100% free inside the platform.
          </p>
        </div>

        {/* Free Testing Mode Disclaimer Box */}
        <div className="mb-8 rounded-2xl border border-emerald-500/30 bg-gradient-to-r from-[#0a1e1b]/70 via-[#0a1526]/80 to-[#0e1629]/70 p-5 sm:p-6 backdrop-blur-md shadow-xl">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-xs font-bold text-emerald-300">
                  Testing Mode Active
                </span>
                <span className="text-sm font-semibold text-white">
                  $0 Free Testing Across All Extensions
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
                {FREE_TESTING_DISCLAIMER}
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <div className="rounded-xl border border-emerald-500/40 bg-slate-900/90 px-4 py-2.5 text-center">
                <div className="text-[11px] text-slate-400 uppercase tracking-wider font-medium">Application Testing Rate</div>
                <div className="text-lg font-bold text-emerald-400 font-mono">
                  $0.00 / FREE<span className="text-xs text-slate-400 font-normal"> (Testing)</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Featured Sample Domains Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
          {showcaseDomains.map((item) => (
            <button
              key={item.domain}
              type="button"
              onClick={() => onSelectExtension(item.domain)}
              className="group relative flex flex-col justify-between rounded-xl p-4 text-left transition-all duration-200 border border-slate-800/80 bg-[#0c1222]/70 hover:border-emerald-500/50 hover:bg-[#111c2e] hover:shadow-lg hover:shadow-emerald-950/20 cursor-pointer"
            >
              <div>
                <div className="flex items-start justify-between gap-1 mb-2">
                  <span className="text-lg font-bold font-mono text-white group-hover:text-emerald-300 transition-colors">
                    {item.domain}
                  </span>
                  <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[9px] font-semibold text-emerald-300 whitespace-nowrap">
                    {item.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2">
                  {item.useCase}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-mono text-emerald-400 font-medium">FREE ($0)</span>
                <span className="text-emerald-400/90 flex items-center gap-0.5 font-medium group-hover:translate-x-0.5 transition-transform">
                  Search <ArrowRight className="h-3 w-3" />
                </span>
              </div>
            </button>
          ))}
        </div>

        {/* Verification Note */}
        <div className="mt-4 flex items-center justify-center sm:justify-start gap-2 text-xs text-slate-400">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          <span>Real registrar availability verification required for official allocation. All tests are free.</span>
        </div>
      </div>
    </section>
  );
};
