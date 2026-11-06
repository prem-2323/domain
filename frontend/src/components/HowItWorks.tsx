import React, { useState } from 'react';
import { Search, ShoppingCart, Server, ArrowRight, CheckCircle2 } from 'lucide-react';

export const HowItWorks: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(0);

  const steps = [
    {
      num: '01',
      title: 'Enter Name & Search',
      icon: Search,
      badge: 'Step 1',
      headline: 'Find your perfect domain across all extensions',
      description:
        'Enter your desired identity (e.g. tala.gy, prem.com, mastertools.in). MasterTools supports searching across all configured extensions.',
      highlights: ['Multi-TLD catalog (.gy, .com, .in)', 'Instant variation generation', 'Real-time validation engine'],
    },
    {
      num: '02',
      title: 'Check Registry Availability',
      icon: CheckCircle2,
      badge: 'Step 2',
      headline: 'Verify with Accredited Registrars',
      description:
        'Domain status is evaluated against registry rules. Unverified names are queued for real-time verification with accredited registrars.',
      highlights: ['Official Registry oversight', 'Free Testing Mode ($0.00)', 'Zero payment collected by MasterTools'],
    },
    {
      num: '03',
      title: 'Choose Registration',
      icon: ShoppingCart,
      badge: 'Step 3',
      headline: 'Register through accredited registrars',
      description:
        'Submit a free registration request with MasterTools for application testing or fulfill via authorized accredited registrar partners.',
      highlights: ['Accredited registrar fulfillment', 'FREE application testing ($0)', 'Free WHOIS privacy protection'],
    },
    {
      num: '04',
      title: 'Connect to Vercel or Render',
      icon: Server,
      badge: 'Step 4',
      headline: 'Cloudflare DNS auto-sync to Vercel & Render',
      description:
        'Select Vercel or Render. MasterTools pre-provisions your Anycast DNS records via Cloudflare with automated Let’s Encrypt SSL certificates.',
      highlights: ['1-click Vercel & Render presets', 'Cloudflare Anycast edge routing', 'Sub-60s global DNS propagation'],
    },
  ];

  return (
    <section id="how-it-works" className="w-full py-16 bg-[#090d1a]/60 border-y border-slate-800/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-3">
            <span>Seamless Workflow</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            How It Works
          </h2>
          <p className="mt-3 text-base text-slate-400">
            From discovering a bold name to serving traffic on modern serverless infrastructure — automated in four simple steps.
          </p>
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isSelected = activeStep === idx;

            return (
              <div
                key={step.num}
                onClick={() => setActiveStep(idx)}
                className={`relative flex flex-col justify-between rounded-2xl p-6 border transition-all duration-300 cursor-pointer ${
                  isSelected
                    ? 'bg-gradient-to-b from-[#131b33] to-[#0c1222] border-indigo-500/80 shadow-xl shadow-indigo-950/40 ring-1 ring-indigo-500/50'
                    : 'bg-[#0c1222]/80 border-slate-800 hover:border-slate-700 hover:bg-[#10172c]'
                }`}
              >
                <div>
                  {/* Step Number & Icon */}
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-md">
                      {step.badge}
                    </span>
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-xl transition-colors ${
                        isSelected
                          ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/40'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>

                  <h3 className="text-xl font-bold text-white mb-2">
                    {step.title}
                  </h3>
                  <h4 className="text-xs font-medium text-indigo-300 mb-2">
                    {step.headline}
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed mb-4">
                    {step.description}
                  </p>
                </div>

                {/* Highlights */}
                <div className="pt-3 border-t border-slate-800/80 space-y-1.5">
                  {step.highlights.map((h, hIdx) => (
                    <div key={hIdx} className="flex items-center gap-1.5 text-[11px] text-slate-300">
                      <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                      <span>{h}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Process Flow Ribbon */}
        <div className="mt-8 flex items-center justify-center gap-2 text-xs font-medium text-slate-400 overflow-x-auto py-2">
          <span className="text-indigo-400 font-semibold">Search</span>
          <ArrowRight className="h-3 w-3 text-slate-600" />
          <span className="text-indigo-400 font-semibold">Register</span>
          <ArrowRight className="h-3 w-3 text-slate-600" />
          <span className="text-blue-400 font-semibold">Connect</span>
          <ArrowRight className="h-3 w-3 text-slate-600" />
          <span className="text-emerald-400 font-semibold">Launch</span>
          <span className="ml-2 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] text-emerald-300 font-mono">
            &lt; 60 seconds total
          </span>
        </div>
      </div>
    </section>
  );
};
