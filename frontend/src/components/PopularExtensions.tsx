import React from 'react';
import { Sparkles, ExternalLink, ShieldCheck, ArrowRight } from 'lucide-react';
import { GY_REGISTRY_INFO } from '../data/extensionCatalog';

interface PopularExtensionsProps {
  onSelectExtension: (domainQuery: string) => void;
  selectedTld?: string;
}

export const PopularExtensions: React.FC<PopularExtensionsProps> = ({
  onSelectExtension,
}) => {
  const showcaseDomains = [
    { name: 'tala', domain: 'tala.gy', useCase: 'Personal Identity & Portfolios', badge: 'Creator' },
    { name: 'prem', domain: 'prem.gy', useCase: 'Short Names & Tech APIs', badge: 'Short & Punchy' },
    { name: 'mastertools', domain: 'mastertools.gy', useCase: 'Cloud & SaaS Platforms', badge: 'Enterprise' },
    { name: 'myshop', domain: 'myshop.gy', useCase: 'Guyana & Global E-Commerce', badge: 'Commerce' },
    { name: 'myportfolio', domain: 'myportfolio.gy', useCase: 'Developer Showcase & Stacks', badge: 'Developer' },
  ];

  return (
    <section id="extensions-section" className="w-full py-10">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Exclusive Country-Code TLD</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              The Official <span className="text-emerald-400 font-mono">.GY</span> Domain Registry
            </h2>
          </div>
          <p className="text-sm text-slate-400 max-w-lg">
            MasterTools Domains focuses exclusively on Guyana's official ccTLD. Managed by the University of Guyana .GY Registry with accredited registrar fulfillment.
          </p>
        </div>

        {/* Registry & Accredited Registrar Information Box */}
        <div className="mb-8 rounded-2xl border border-emerald-500/30 bg-gradient-to-r from-[#0a1e1b]/70 via-[#0a1526]/80 to-[#0e1629]/70 p-5 sm:p-6 backdrop-blur-md shadow-xl">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-xs font-bold text-emerald-300">
                  Registry Authority
                </span>
                <span className="text-sm font-semibold text-white">
                  {GY_REGISTRY_INFO.registryName}
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
                {GY_REGISTRY_INFO.description} All names are registered through accredited registrars.
                Pricing is transparent at standard registrar rates (~${GY_REGISTRY_INFO.standardAnnualPrice.toFixed(2)}/yr) with zero hidden markup.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
              <div className="rounded-xl border border-slate-700/80 bg-slate-900/90 px-4 py-2.5 text-center">
                <div className="text-[11px] text-slate-400 uppercase tracking-wider font-medium">Standard Registrar Rate</div>
                <div className="text-lg font-bold text-emerald-400 font-mono">
                  ${GY_REGISTRY_INFO.standardAnnualPrice.toFixed(2)}<span className="text-xs text-slate-400 font-normal"> / year</span>
                </div>
              </div>

              <a
                href={GY_REGISTRY_INFO.directoryUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 px-4 py-2.5 text-xs font-semibold text-emerald-300 transition-all shadow-sm"
              >
                <span>Accredited Registrars</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </div>

        {/* Featured Sample .GY Domains Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
          {showcaseDomains.map((item) => (
            <button
              key={item.domain}
              type="button"
              onClick={() => onSelectExtension(item.name)}
              className="group relative flex flex-col justify-between rounded-xl p-4 text-left transition-all duration-200 border border-slate-800/80 bg-[#0c1220]/70 hover:border-emerald-500/50 hover:bg-[#111c2e] hover:shadow-lg hover:shadow-emerald-950/20 cursor-pointer"
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
                <span className="font-mono text-emerald-400 font-medium">~$45.00/yr</span>
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
          <span>Real-time availability confirmed directly with accredited .GY registrar registry endpoints.</span>
        </div>
      </div>
    </section>
  );
};
