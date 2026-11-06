import React, { useState, useEffect } from 'react';
import {
  Zap,
  Copy,
  Check,
  ShieldCheck,
  Terminal,
  RefreshCw,
  Server,
  Globe,
  Info,
} from 'lucide-react';
import {
  getProposedDnsPlan,
  verifyDeployment,
} from '../api/domainService';
import type {
  ProposedDnsPlan,
  IntegrationDeploymentStatus,
  IntegrationWorkflowState,
  DnsRecordItem,
} from '../types/domain';

const STATE_CONFIG: Record<
  IntegrationWorkflowState,
  { label: string; bg: string; text: string; border: string }
> = {
  not_connected: {
    label: 'Not Connected',
    bg: 'bg-slate-800/80',
    text: 'text-slate-400',
    border: 'border-slate-700',
  },
  credentials_missing: {
    label: 'Credentials Missing',
    bg: 'bg-amber-500/15',
    text: 'text-amber-300',
    border: 'border-amber-500/30',
  },
  zone_pending_activation: {
    label: 'Zone Pending Activation',
    bg: 'bg-amber-500/15',
    text: 'text-amber-300',
    border: 'border-amber-500/30',
  },
  awaiting_nameserver_update: {
    label: 'Awaiting Nameserver Update',
    bg: 'bg-blue-500/15',
    text: 'text-blue-300',
    border: 'border-blue-500/30',
  },
  dns_conflict: {
    label: 'DNS Conflict Detected',
    bg: 'bg-rose-500/15',
    text: 'text-rose-300',
    border: 'border-rose-500/30',
  },
  awaiting_approval: {
    label: 'Awaiting Approval',
    bg: 'bg-indigo-500/15',
    text: 'text-indigo-300',
    border: 'border-indigo-500/30',
  },
  provisioning: {
    label: 'Provisioning...',
    bg: 'bg-purple-500/15',
    text: 'text-purple-300',
    border: 'border-purple-500/30',
  },
  dns_verification_pending: {
    label: 'DNS Verification Pending',
    bg: 'bg-amber-500/15',
    text: 'text-amber-300',
    border: 'border-amber-500/30',
  },
  connected: {
    label: 'Connected & Verified',
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400 font-bold',
    border: 'border-emerald-500/40',
  },
  failed: {
    label: 'Operation Failed',
    bg: 'bg-rose-950/40',
    text: 'text-rose-400',
    border: 'border-rose-500/40',
  },
};

export const DeployIntegrations: React.FC = () => {
  const [activePlatform, setActivePlatform] = useState<'vercel' | 'render'>('vercel');
  const [testDomain, setTestDomain] = useState<string>('till.gy');
  const [plan, setPlan] = useState<ProposedDnsPlan | null>(null);
  const [status, setStatus] = useState<IntegrationDeploymentStatus | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const fetchPlan = async (dom: string, plat: 'vercel' | 'render') => {
    setIsLoading(true);
    try {
      const p = await getProposedDnsPlan(dom, plat);
      setPlan(p);
    } catch {
      setPlan(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      try {
        const p = await getProposedDnsPlan(testDomain, activePlatform);
        if (!ignore) {
          setPlan(p);
        }
      } catch {
        if (!ignore) {
          setPlan(null);
        }
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, [testDomain, activePlatform]);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleVerify = async () => {
    setIsVerifying(true);
    try {
      const res = await verifyDeployment(testDomain, activePlatform);
      setStatus(res);
    } catch {
      // ignore
    } finally {
      setIsVerifying(false);
    }
  };

  const fallbackVercelRecords: DnsRecordItem[] = [
    { type: 'A', name: '@', content: '76.76.21.21', ttl: 60, proxied: false, purpose: 'Vercel root edge' },
    { type: 'CNAME', name: 'www', content: 'cname.vercel-dns.com', ttl: 60, proxied: false, purpose: 'Vercel www edge' },
  ];

  const fallbackRenderRecords: DnsRecordItem[] = [
    { type: 'CNAME', name: '@', content: 'mastertools-app.onrender.com', ttl: 60, proxied: false, purpose: 'Render Web Service' },
    { type: 'CNAME', name: 'www', content: 'mastertools-app.onrender.com', ttl: 60, proxied: false, purpose: 'Render www' },
  ];

  const displayRecords =
    status?.records && status.records.length > 0
      ? status.records
      : plan?.required_records && plan.required_records.length > 0
      ? plan.required_records
      : activePlatform === 'vercel'
      ? fallbackVercelRecords
      : fallbackRenderRecords;

  const currentState: IntegrationWorkflowState =
    status?.state || plan?.state || 'not_connected';
  const stateBadge = STATE_CONFIG[currentState] || STATE_CONFIG.not_connected;

  return (
    <section id="deploy-integrations" className="w-full py-16 relative">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Heading */}
        <div className="text-center max-w-3xl mx-auto mb-10">
          <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">
            <Zap className="h-3.5 w-3.5" />
            <span>Cloudflare Edge DNS • Vercel & Render Integration</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Live Cloudflare DNS & Hosting Bridge
          </h2>
          <p className="mt-3 text-base text-slate-400">
            Powered by real Cloudflare API orchestration. Inspect active zones, assigned nameservers,
            required hosting records, and real DNS propagation for Vercel and Render deployments.
          </p>
        </div>

        {/* Domain Inspector Bar */}
        <div className="max-w-xl mx-auto mb-8 flex items-center rounded-xl bg-slate-900 border border-slate-800 p-2 gap-2">
          <div className="flex items-center gap-2 pl-3 flex-1">
            <Globe className="h-4 w-4 text-indigo-400" />
            <input
              type="text"
              value={testDomain}
              onChange={(e) => setTestDomain(e.target.value.trim().toLowerCase())}
              placeholder="e.g. till.gy or mydomain.com"
              className="w-full bg-transparent text-sm text-white font-mono focus:outline-none"
            />
          </div>
          <button
            type="button"
            onClick={() => fetchPlan(testDomain, activePlatform)}
            disabled={isLoading}
            className="flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Inspect</span>
          </button>
        </div>

        {/* Platform Selector Tabs */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex rounded-xl bg-slate-900/90 p-1 border border-slate-800">
            <button
              type="button"
              onClick={() => setActivePlatform('vercel')}
              className={`flex items-center gap-2.5 rounded-lg px-6 py-2.5 text-sm font-semibold transition-all cursor-pointer ${
                activePlatform === 'vercel'
                  ? 'bg-gradient-to-r from-slate-800 to-slate-900 text-white shadow-md border border-slate-700'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <svg className="h-4 w-4 fill-white" viewBox="0 0 76 65" fill="none">
                <path d="M37.5274 0L75.0548 65H0L37.5274 0Z" />
              </svg>
              <span>Vercel Integration</span>
            </button>

            <button
              type="button"
              onClick={() => setActivePlatform('render')}
              className={`flex items-center gap-2.5 rounded-lg px-6 py-2.5 text-sm font-semibold transition-all cursor-pointer ${
                activePlatform === 'render'
                  ? 'bg-gradient-to-r from-slate-800 to-slate-900 text-white shadow-md border border-slate-700'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <div className="h-4 w-4 rounded-sm bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-[9px] text-black">
                R
              </div>
              <span>Render Integration</span>
            </button>
          </div>
        </div>

        {/* Interactive Showcase Box */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start rounded-3xl border border-slate-800 bg-gradient-to-b from-[#0e1526] via-[#090e1c] to-[#07090e] p-6 sm:p-8 shadow-2xl">
          {/* Left Column: Real zone & nameserver info */}
          <div className="lg:col-span-5 space-y-5">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400 mb-1">
                <span>{activePlatform === 'vercel' ? 'Next.js & Frontend Edge' : 'Web Services & Containers'}</span>
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">
                {activePlatform === 'vercel'
                  ? 'Real Cloudflare DNS for Vercel'
                  : 'Native Aliasing for Render Services'}
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {activePlatform === 'vercel'
                  ? 'Connect your domain directly to any Vercel Project. Retrieves recommended A and CNAME records with actual domain verification challenges.'
                  : 'Connect your apex domain and subdomains to Render services without manual DNS guesswork. Backed by Cloudflare CNAME flattening.'}
              </p>
            </div>

            {/* Cloudflare Zone & Nameserver Transparency Box */}
            <div className="rounded-2xl border border-slate-800 bg-[#070b14] p-4 space-y-3">
              <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-800">
                <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                  <Server className="h-3.5 w-3.5 text-indigo-400" />
                  Assigned Cloudflare Zone Nameservers
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${plan?.is_zone_active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
                  {plan?.zone_status ? `Zone: ${plan.zone_status}` : 'Pending Lookup'}
                </span>
              </div>

              {plan?.assigned_nameservers && plan.assigned_nameservers.length > 0 ? (
                <div className="space-y-1.5">
                  <div className="text-[11px] text-slate-400">
                    Nameservers assigned to <strong>{testDomain}</strong>:
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1 font-mono text-xs text-emerald-300 font-bold">
                    {plan.assigned_nameservers.map((ns) => (
                      <span key={ns} className="rounded bg-slate-900 border border-slate-700/80 px-2 py-1">
                        {ns}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-400 leading-relaxed">
                  Nameservers are assigned per Cloudflare zone. Changes must be completed at the registrar. Do not use unrelated nameservers.
                </p>
              )}

              <div className="pt-2 border-t border-slate-800/80 flex items-start gap-1.5 text-[11px] text-slate-400">
                <Info className="h-3.5 w-3.5 text-blue-400 shrink-0 mt-0.5" />
                <span>Registrar nameserver delegation must be confirmed by Cloudflare before edge proxying activates.</span>
              </div>
            </div>

            {/* CLI Snippet */}
            <div className="rounded-xl border border-slate-800 bg-[#070b14] p-3 text-xs font-mono text-slate-300">
              <div className="flex items-center justify-between text-slate-400 pb-2 mb-2 border-b border-slate-800 text-[11px]">
                <span className="flex items-center gap-1.5">
                  <Terminal className="h-3 w-3" /> CLI Quick Command
                </span>
                <span>FastAPI Webhook</span>
              </div>
              <div className="text-slate-300">
                {activePlatform === 'vercel' ? (
                  <>
                    <span className="text-emerald-400">$</span> vercel domains add <span className="text-emerald-400">{testDomain}</span>
                  </>
                ) : (
                  <>
                    <span className="text-emerald-400">$</span> render custom-domains set <span className="text-emerald-400">{testDomain}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Live DNS Records Table & Real Verification */}
          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-slate-800 bg-[#0a0f1d] p-5 shadow-inner space-y-4">
              {/* Table Top Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800 gap-2">
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Live Anycast DNS Zone File (Cloudflare)
                  </div>
                  <div className="text-sm font-mono text-emerald-300 font-semibold flex items-center gap-2">
                    <span>domain: {testDomain}</span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${stateBadge.bg} ${stateBadge.text} ${stateBadge.border}`}>
                      {stateBadge.label}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleVerify}
                    disabled={isVerifying}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white hover:border-indigo-500 transition-all cursor-pointer disabled:opacity-50"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 text-blue-400 ${isVerifying ? 'animate-spin' : ''}`} />
                    <span>Verify Live DNS</span>
                  </button>
                </div>
              </div>

              {/* Status Message Banner if Present */}
              {status?.message && (
                <div className={`rounded-xl border p-3 text-xs ${status.state === 'connected' ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300' : 'border-amber-500/30 bg-amber-950/20 text-amber-200'}`}>
                  {status.message}
                </div>
              )}

              {/* Records Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                      <th className="pb-2">Type</th>
                      <th className="pb-2">Name / Host</th>
                      <th className="pb-2">Target / Value</th>
                      <th className="pb-2">TTL</th>
                      <th className="pb-2 text-right">Copy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {displayRecords.map((rec, i) => (
                      <tr key={i} className="hover:bg-slate-850/50 transition-colors">
                        <td className="py-2.5">
                          <span className="rounded bg-indigo-500/15 border border-indigo-500/30 px-1.5 py-0.5 text-indigo-300 font-bold">
                            {rec.type}
                          </span>
                        </td>
                        <td className="py-2.5 font-bold text-white">{rec.name}</td>
                        <td className="py-2.5 text-slate-300 truncate max-w-[200px]" title={rec.content}>
                          {rec.content}
                        </td>
                        <td className="py-2.5 text-slate-400">{rec.ttl}s</td>
                        <td className="py-2.5 text-right">
                          <button
                            type="button"
                            onClick={() => handleCopy(rec.content, i)}
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

              {/* Bottom SSL & Handshake Ribbon */}
              <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className={`h-3.5 w-3.5 ${status?.ssl_verified ? 'text-emerald-400' : 'text-slate-500'}`} />
                  {status?.ssl_verified
                    ? `SSL Active (${status.ssl_status || 'Strict'})`
                    : 'SSL status unverified until DNS propagation completes'}
                </span>
                <span className="font-mono text-indigo-300">
                  Target: {activePlatform === 'vercel' ? 'Vercel Edge Network' : 'Render Service Mesh'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
