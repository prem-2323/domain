import React, { useState } from 'react';
import {
  Zap,
  CheckCircle2,
  Copy,
  Check,
  ShieldCheck,
  Terminal,
  RefreshCw,
} from 'lucide-react';

export const DeployIntegrations: React.FC = () => {
  const [activePlatform, setActivePlatform] = useState<'vercel' | 'render'>('vercel');
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifiedStatus, setVerifiedStatus] = useState<string>('DNS Propagated • Active');

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleVerify = () => {
    setIsVerifying(true);
    setVerifiedStatus('Querying Anycast edge nodes...');
    setTimeout(() => {
      setIsVerifying(false);
      setVerifiedStatus('All Records Verified • SSL Active');
    }, 800);
  };

  const vercelRecords = [
    { type: 'A', name: '@', value: '76.76.21.21', ttl: '60s' },
    { type: 'CNAME', name: 'www', value: 'cname.vercel-dns.com', ttl: '60s' },
    { type: 'TXT', name: '_vercel', value: 'vc-domain-verify=mastertools-auth-token-9821', ttl: '300s' },
  ];

  const renderRecords = [
    { type: 'ALIAS', name: '@', value: 'srv-mastertools-app.onrender.com', ttl: '60s' },
    { type: 'CNAME', name: 'www', value: 'srv-mastertools-app.onrender.com', ttl: '60s' },
    { type: 'TXT', name: '_render', value: 'render-verify=rnd_7823ab192084df92', ttl: '300s' },
  ];

  const activeRecords = activePlatform === 'vercel' ? vercelRecords : renderRecords;

  return (
    <section id="deploy-integrations" className="w-full py-16 relative">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">
            <Zap className="h-3.5 w-3.5" />
            <span>Cloudflare Edge DNS • Vercel & Render</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Connect Your <span className="text-emerald-400 font-mono">.GY</span> Domain to Vercel & Render
          </h2>
          <p className="mt-3 text-base text-slate-400">
            Powered by Cloudflare Anycast DNS. MasterTools automatically manages your .gy zone files,
            provisioning instant edge routing and automated SSL certificates for Vercel and Render deployments.
          </p>
        </div>

        {/* Platform Selector Tabs */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex rounded-xl bg-slate-900/90 p-1 border border-slate-800">
            <button
              type="button"
              onClick={() => setActivePlatform('vercel')}
              className={`flex items-center gap-2.5 rounded-lg px-6 py-2.5 text-sm font-semibold transition-all ${
                activePlatform === 'vercel'
                  ? 'bg-gradient-to-r from-slate-800 to-slate-900 text-white shadow-md border border-slate-700'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {/* Vercel Triangle Logo SVG */}
              <svg className="h-4 w-4 fill-white" viewBox="0 0 76 65" fill="none">
                <path d="M37.5274 0L75.0548 65H0L37.5274 0Z" />
              </svg>
              <span>Vercel Integration</span>
            </button>

            <button
              type="button"
              onClick={() => setActivePlatform('render')}
              className={`flex items-center gap-2.5 rounded-lg px-6 py-2.5 text-sm font-semibold transition-all ${
                activePlatform === 'render'
                  ? 'bg-gradient-to-r from-slate-800 to-slate-900 text-white shadow-md border border-slate-700'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {/* Render Cube Icon */}
              <div className="h-4 w-4 rounded-sm bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-[9px] text-black">
                R
              </div>
              <span>Render Integration</span>
            </button>
          </div>
        </div>

        {/* Interactive Showcase Box */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded-3xl border border-slate-800 bg-gradient-to-b from-[#0e1526] via-[#090e1c] to-[#07090e] p-6 sm:p-8 shadow-2xl">
          {/* Left Column: Feature highlights */}
          <div className="lg:col-span-5 space-y-6">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400 mb-1">
                <span>{activePlatform === 'vercel' ? 'Next.js & Frontend Edge' : 'Web Services & PostgreSQL'}</span>
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">
                {activePlatform === 'vercel'
                  ? 'Zero-touch DNS for Vercel Deployments'
                  : 'Native Aliasing for Render Web Services'}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {activePlatform === 'vercel'
                  ? 'Connect your purchased domain directly to any Vercel Project. We automatically register root A records and wildcard CNAMEs with instant Let’s Encrypt edge certificates.'
                  : 'Point your apex domain and subdomains to Render services without ALIAS/ANAME record headaches. Fully compatible with Docker containers, web services, and background workers.'}
              </p>
            </div>

            {/* Benefit Checkpoints */}
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-white">Automated DNS Record Provisioning</h4>
                  <p className="text-xs text-slate-400">
                    No copy-pasting IPs or guessing TTL settings. MasterTools syncs the exact zone file via API.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-white">Sub-Minute Global Propagation</h4>
                  <p className="text-xs text-slate-400">
                    Propagated across 300+ Anycast edge PoPs worldwide in under 60 seconds with 60s TTL.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-white">Automatic SSL Handshake & HSTS</h4>
                  <p className="text-xs text-slate-400">
                    Full Let's Encrypt automated TLS issuance with zero manual cert uploads.
                  </p>
                </div>
              </div>
            </div>

            {/* CLI Snippet preview */}
            <div className="rounded-xl border border-slate-800 bg-[#070b14] p-3 text-xs font-mono text-slate-300">
              <div className="flex items-center justify-between text-slate-400 pb-2 mb-2 border-b border-slate-800 text-[11px]">
                <span className="flex items-center gap-1.5">
                  <Terminal className="h-3 w-3" /> CLI Quick Sync
                </span>
                <span>FastAPI Webhook</span>
              </div>
              <div className="text-slate-300">
                {activePlatform === 'vercel' ? (
                  <>
                    <span className="text-emerald-400">$</span> vercel domains add <span className="text-emerald-400">tala.gy</span>
                  </>
                ) : (
                  <>
                    <span className="text-emerald-400">$</span> render custom-domains set <span className="text-emerald-400">tala.gy</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Live DNS Records Table & Simulator */}
          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-slate-800 bg-[#0a0f1d] p-5 shadow-inner">
              {/* Table Top Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-4 border-b border-slate-800 gap-2">
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Live Anycast DNS Zone File (Cloudflare)
                  </div>
                  <div className="text-sm font-mono text-emerald-300 font-semibold">
                    domain: tala.gy
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleVerify}
                    disabled={isVerifying}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white hover:border-indigo-500 transition-all cursor-pointer"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 text-blue-400 ${isVerifying ? 'animate-spin' : ''}`} />
                    <span>Verify Records</span>
                  </button>

                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 text-xs font-medium text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>{verifiedStatus}</span>
                  </span>
                </div>
              </div>

              {/* Records Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                      <th className="pb-2">Type</th>
                      <th className="pb-2">Name / Host</th>
                      <th className="pb-2">Value / Target</th>
                      <th className="pb-2">TTL</th>
                      <th className="pb-2 text-right">Copy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {activeRecords.map((rec, i) => (
                      <tr key={i} className="hover:bg-slate-850/50 transition-colors">
                        <td className="py-2.5">
                          <span className="rounded bg-indigo-500/15 border border-indigo-500/30 px-1.5 py-0.5 text-indigo-300 font-bold">
                            {rec.type}
                          </span>
                        </td>
                        <td className="py-2.5 font-bold text-white">{rec.name}</td>
                        <td className="py-2.5 text-slate-300 truncate max-w-[200px]" title={rec.value}>
                          {rec.value}
                        </td>
                        <td className="py-2.5 text-slate-400">{rec.ttl}</td>
                        <td className="py-2.5 text-right">
                          <button
                            type="button"
                            onClick={() => handleCopy(rec.value, i)}
                            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                            aria-label="Copy record value"
                          >
                            {copiedIndex === i ? (
                              <Check className="h-3.5 w-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Simulation Architecture Ribbon */}
              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  DNSSEC Enabled & Signed
                </span>
                <span className="font-mono text-indigo-300">
                  Target: {activePlatform === 'vercel' ? 'Vercel Edge Network' : 'Render Global Service Mesh'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
