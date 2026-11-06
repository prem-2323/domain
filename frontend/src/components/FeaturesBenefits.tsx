import React from 'react';
import {
  ShieldCheck,
  Zap,
  Lock,
  RefreshCw,
  Terminal,
  CheckCircle,
  Cpu,
  Layers,
} from 'lucide-react';

export const FeaturesBenefits: React.FC = () => {
  const features = [
    {
      icon: Zap,
      iconColor: 'text-blue-400',
      bgColor: 'bg-blue-500/10 border-blue-500/20',
      title: 'Ultra-Fast Anycast DNS',
      description:
        'Global anycast DNS routed through 300+ Tier-1 edge PoPs. Achieve sub-10ms lookup times from Tokyo to San Francisco with 99.999% SLA.',
    },
    {
      icon: ShieldCheck,
      iconColor: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10 border-emerald-500/20',
      title: 'Free WHOIS Privacy Forever',
      description:
        'Never pay extra to hide your personal address, phone number, and inbox from spammers. WHOIS protection is bundled at $0 for the life of your domain.',
    },
    {
      icon: Layers,
      iconColor: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10 border-indigo-500/20',
      title: 'Instant Cloud Presets',
      description:
        'Pre-configured 1-click DNS blueprints for Vercel, Render, Cloudflare, Supabase, and AWS. Zero manual record entry or typo risk.',
    },
    {
      icon: RefreshCw,
      iconColor: 'text-purple-400',
      bgColor: 'bg-purple-500/10 border-purple-500/20',
      title: 'Transparent Renewals',
      description:
        'No hidden markups or renewal shock. We clearly display your renewal rate upfront so you are never surprised when your subscription renews.',
    },
    {
      icon: Terminal,
      iconColor: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10 border-cyan-500/20',
      title: 'Developer REST & FastAPI Engine',
      description:
        'Programmatic DNS record automation via modern REST APIs. Easily integrate domain registration, availability lookups, and webhooks into your pipeline.',
    },
    {
      icon: Lock,
      iconColor: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/20',
      title: 'Two-Factor & Registrar Lock',
      description:
        'Enterprise domain defense against unauthorized transfers, DNS cache poisoning, and hijacking. Native DNSSEC signing included on supported TLDs.',
    },
  ];

  return (
    <section id="features-section" className="w-full py-16 bg-[#070b14]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-3">
            <Cpu className="h-3.5 w-3.5" />
            <span>Built for Modern Builders</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Why Builders Choose MasterTools Domains
          </h2>
          <p className="mt-3 text-base text-slate-400">
            A developer-first domain experience. No legacy bloatware, aggressive upsell modals, or complex DNS control panels.
          </p>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <div
                key={i}
                className="group relative flex flex-col justify-between rounded-2xl border border-slate-800 bg-[#0c1220]/80 p-6 transition-all duration-300 hover:border-slate-700 hover:bg-[#0f172a] hover:shadow-xl hover:shadow-black/50"
              >
                <div>
                  <div
                    className={`inline-flex h-12 w-12 items-center justify-center rounded-xl border ${feature.bgColor} ${feature.iconColor} mb-5 transition-transform group-hover:scale-105`}
                  >
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 group-hover:text-indigo-300 transition-colors">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    {feature.description}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-800/60 flex items-center gap-1.5 text-xs text-indigo-400/90 font-medium">
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Standard on all plans</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
