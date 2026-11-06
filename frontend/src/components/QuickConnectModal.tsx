import React, { useState, useEffect } from 'react';
import {
  X,
  Server,
  Zap,
  CheckCircle2,
  Copy,
  Check,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import type {
  DomainSearchResult,
  ProposedDnsPlan,
  IntegrationDeploymentStatus,
  IntegrationWorkflowState,
} from '../types/domain';
import {
  getProposedDnsPlan,
  applyDnsPlan,
  verifyDeployment,
  RegistrationApiError,
} from '../api/domainService';

interface QuickConnectModalProps {
  domainItem: DomainSearchResult | null;
  onClose: () => void;
}

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
    label: 'Awaiting Explicit Approval',
    bg: 'bg-indigo-500/15',
    text: 'text-indigo-300',
    border: 'border-indigo-500/30',
  },
  provisioning: {
    label: 'Provisioning DNS Records...',
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

export const QuickConnectModal: React.FC<QuickConnectModalProps> = ({
  domainItem,
  onClose,
}) => {
  const [target, setTarget] = useState<'vercel' | 'render'>('vercel');
  const [copied, setCopied] = useState(false);
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [plan, setPlan] = useState<ProposedDnsPlan | null>(null);
  const [status, setStatus] = useState<IntegrationDeploymentStatus | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [overrideApproved, setOverrideApproved] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const domain = domainItem?.domain || '';

  const loadPlan = async (selectedTarget: 'vercel' | 'render') => {
    if (!domain) return;
    setIsLoadingPlan(true);
    setErrorMessage(null);
    setOverrideApproved(false);
    try {
      const p = await getProposedDnsPlan(domain, selectedTarget);
      setPlan(p);
    } catch (err) {
      const msg = err instanceof RegistrationApiError ? err.message : 'Failed to retrieve DNS plan.';
      setErrorMessage(msg);
    } finally {
      setIsLoadingPlan(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    if (!domainItem) return;
    const run = async () => {
      try {
        const p = await getProposedDnsPlan(domainItem.domain, target);
        if (!ignore) {
          setPlan(p);
          setStatus(null);
          setErrorMessage(null);
        }
      } catch (err) {
        if (!ignore) {
          const msg = err instanceof RegistrationApiError ? err.message : 'Failed to retrieve DNS plan.';
          setErrorMessage(msg);
        }
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, [domainItem, target]);

  if (!domainItem) return null;

  const currentState: IntegrationWorkflowState =
    status?.state || plan?.state || 'not_connected';
  const stateBadge = STATE_CONFIG[currentState] || STATE_CONFIG.not_connected;

  const handleApplyChanges = async () => {
    if (!plan) return;
    setIsApplying(true);
    setErrorMessage(null);

    try {
      const res = await applyDnsPlan({
        domain,
        target_platform: target,
        plan_id: plan.plan_id || '',
        plan_signature: plan.plan_signature || '',
        expires_at: plan.expires_at || '',
        approved: true,
        override_conflicts: overrideApproved,
      });
      setStatus(res);
      // Reload plan to refresh existing records and conflicts
      await loadPlan(target);
    } catch (err) {
      const msg = err instanceof RegistrationApiError ? err.message : 'Failed to apply DNS changes.';
      setErrorMessage(msg);
    } finally {
      setIsApplying(false);
    }
  };

  const handleVerify = async () => {
    setIsVerifying(true);
    setErrorMessage(null);
    try {
      const res = await verifyDeployment(domain, target);
      setStatus(res);
    } catch (err) {
      const msg = err instanceof RegistrationApiError ? err.message : 'Verification failed.';
      setErrorMessage(msg);
    } finally {
      setIsVerifying(false);
    }
  };

  const recordsToDisplay =
    status?.records && status.records.length > 0
      ? status.records
      : plan?.required_records || [];

  const handleCopyAll = () => {
    const text = recordsToDisplay
      .map((r) => `${r.type}\t${r.name}\t${r.content}`)
      .join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />

      <div className="relative w-full max-w-2xl rounded-3xl border border-slate-800 bg-[#0c1222] p-5 sm:p-7 shadow-2xl z-10 my-8">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30">
            <Server className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                Cloudflare + Cloud Bridge
              </span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${stateBadge.bg} ${stateBadge.text} ${stateBadge.border}`}>
                {stateBadge.label}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono flex items-center gap-1.5 mt-0.5">
              <span>Connect</span>
              <span className="text-emerald-400 font-extrabold">{domain}</span>
            </h2>
          </div>
        </div>

        {/* Destination Platform Switcher */}
        <div className="mb-5">
          <label className="text-xs text-slate-400 block mb-2 font-medium">
            Select Cloud Destination:
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTarget('vercel')}
              className={`flex items-center gap-2.5 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                target === 'vercel'
                  ? 'border-indigo-500 bg-indigo-950/40 ring-1 ring-indigo-500/50'
                  : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
              }`}
            >
              <svg className="h-5 w-5 fill-white shrink-0" viewBox="0 0 76 65">
                <path d="M37.5274 0L75.0548 65H0L37.5274 0Z" />
              </svg>
              <div>
                <div className="text-xs font-bold text-white">Vercel</div>
                <div className="text-[10px] text-slate-400">Serverless & Edge</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setTarget('render')}
              className={`flex items-center gap-2.5 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                target === 'render'
                  ? 'border-emerald-500 bg-emerald-950/40 ring-1 ring-emerald-500/50'
                  : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
              }`}
            >
              <div className="h-5 w-5 rounded bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-[10px] text-black shrink-0">
                R
              </div>
              <div>
                <div className="text-xs font-bold text-white">Render</div>
                <div className="text-[10px] text-slate-400">Web Services & Docker</div>
              </div>
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* State Banner 1: Credentials Missing */}
        {currentState === 'credentials_missing' && (
          <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-950/20 p-3.5 text-xs text-amber-200/90 space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-amber-300">
              <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
              <span>Backend API Credentials Required</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              {plan?.message || 'Cloudflare, Vercel, or Render API credentials are not configured on the backend server.'}
              You can still view the required DNS records below to configure them manually in Cloudflare.
            </p>
          </div>
        )}

        {/* State Banner 2: Nameservers Update Required */}
        {(currentState === 'awaiting_nameserver_update' || currentState === 'zone_pending_activation') && (
          <div className="mb-4 rounded-2xl border border-blue-500/30 bg-blue-950/20 p-4 text-xs text-blue-200 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-bold text-blue-300 flex items-center gap-1.5">
                <ShieldAlert className="h-4 w-4 text-blue-400" />
                Cloudflare Zone Nameserver Setup Required
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold">
                {plan?.zone_status || 'Pending'}
              </span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Cloudflare has assigned dedicated nameservers for this zone. You must update your registrar's nameservers
              to these exact values. <em>Do not use nameservers from unrelated domains.</em>
            </p>
            {plan?.assigned_nameservers && plan.assigned_nameservers.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-[#070b14] p-3 space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                  Assigned Nameservers for {domain}:
                </div>
                <div className="flex flex-wrap gap-2 pt-1 font-mono text-xs text-emerald-300 font-bold">
                  {plan.assigned_nameservers.map((ns) => (
                    <span key={ns} className="rounded bg-slate-900 border border-slate-700 px-2 py-1">
                      {ns}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* State Banner 3: DNS Conflict Warning */}
        {currentState === 'dns_conflict' && plan?.has_conflicts && (
          <div className="mb-4 rounded-2xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs text-rose-200 space-y-3">
            <div className="flex items-center gap-2 font-bold text-rose-300 text-sm">
              <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
              <span>Conflicting DNS Records Detected</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Existing records in your Cloudflare zone point to a different destination.
              To avoid unintended service downtime, changes are not applied automatically.
            </p>
            <div className="space-y-1.5 font-mono text-[11px]">
              {plan.conflicts.map((c, idx) => (
                <div key={idx} className="rounded-lg bg-slate-900/90 border border-rose-500/30 p-2.5 text-slate-300">
                  <div className="text-rose-400 font-semibold">{c.message}</div>
                  <div className="text-[10px] text-slate-400 mt-1">
                    Existing: {c.existing_record.type} {c.existing_record.name} → {c.existing_record.content}
                  </div>
                </div>
              ))}
            </div>

            <label className="flex items-center gap-2 pt-1 text-xs text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={overrideApproved}
                onChange={(e) => setOverrideApproved(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="font-semibold text-rose-300">
                I explicitly approve updating/replacing these conflicting DNS records in Cloudflare.
              </span>
            </label>
          </div>
        )}

        {/* DNS Records Box */}
        <div className="rounded-2xl border border-slate-800 bg-[#080d19] p-4 mb-5">
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-300">
                {target === 'vercel' ? 'Vercel' : 'Render'} Required DNS Records
              </span>
              {isLoadingPlan && <RefreshCw className="h-3 w-3 animate-spin text-slate-400" />}
            </div>
            <button
              type="button"
              onClick={handleCopyAll}
              className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
              <span>{copied ? 'Copied!' : 'Copy All'}</span>
            </button>
          </div>

          <div className="space-y-2 text-xs font-mono">
            {recordsToDisplay.length === 0 ? (
              <div className="py-4 text-center text-slate-500 text-xs font-sans">
                {isLoadingPlan ? 'Querying exact DNS requirements from backend...' : 'No DNS records currently generated.'}
              </div>
            ) : (
              recordsToDisplay.map((r, i) => {
                const verItem = status?.verification_items?.find(
                  (v) => v.type === r.type && (v.name.includes(r.name) || r.name === '@')
                );

                return (
                  <div
                    key={i}
                    className="flex flex-col sm:flex-row sm:items-center justify-between rounded-lg bg-slate-900/90 border border-slate-800/80 p-2.5 text-slate-300 gap-1.5"
                  >
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-indigo-300 font-bold text-[10px]">
                        {r.type}
                      </span>
                      <span className="text-white font-semibold">{r.name}</span>
                      <span className="text-slate-500">→</span>
                      <span className="text-slate-200 truncate max-w-[200px]" title={r.content}>
                        {r.content}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[10px] font-sans">
                      {verItem ? (
                        verItem.verified ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                            <Check className="h-3 w-3" /> Live in DNS
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-400">
                            <RefreshCw className="h-3 w-3 animate-spin" /> Propagating
                          </span>
                        )
                      ) : (
                        <span className="text-slate-400">{r.purpose || 'Routing'}</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* SSL / TLS Status Banner */}
          <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className={`h-4 w-4 ${status?.ssl_verified ? 'text-emerald-400' : 'text-slate-500'}`} />
              <span>
                {status?.ssl_verified
                  ? `SSL Mode: Active (${status?.ssl_status || 'Strict'})`
                  : 'SSL status unverified until DNS & platform verification complete'}
              </span>
            </div>
            {plan?.zone_name && (
              <span className="font-mono text-slate-500 text-[10px]">
                Zone: {plan.zone_name}
              </span>
            )}
          </div>
        </div>

        {/* Action Controls & Real Success Banner */}
        {currentState === 'connected' ? (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-center space-y-2">
            <div className="flex items-center justify-center gap-2 text-emerald-400 font-semibold text-sm">
              <CheckCircle2 className="h-5 w-5" />
              <span>Deployment Connection Live & Verified!</span>
            </div>
            <p className="text-xs text-slate-300">
              Cloudflare Anycast routing is active for <strong>{domain}</strong> and verified with{' '}
              {target === 'vercel' ? 'Vercel Edge Network' : 'Render Web Services'}.
            </p>
            <div className="pt-2 flex items-center justify-center gap-3">
              <a
                href={`https://${domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 transition-colors"
              >
                <span>Visit https://{domain}</span>
                <ExternalLink className="h-3 w-3" />
              </a>
              <button
                type="button"
                onClick={handleVerify}
                disabled={isVerifying}
                className="inline-flex items-center gap-1 rounded-xl bg-slate-800 border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white"
              >
                <RefreshCw className={`h-3 w-3 ${isVerifying ? 'animate-spin' : ''}`} />
                <span>Re-verify</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex gap-2">
              <button
                type="button"
                disabled={
                  isApplying ||
                  !plan?.can_apply ||
                  (currentState === 'dns_conflict' && !overrideApproved)
                }
                onClick={handleApplyChanges}
                className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 hover:brightness-110 active:scale-[0.99] transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                {isApplying ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Applying Changes to Cloudflare...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    <span>
                      {currentState === 'dns_conflict'
                        ? 'Override & Apply Approved DNS Records'
                        : `Approve & Apply ${target === 'vercel' ? 'Vercel' : 'Render'} DNS`}
                    </span>
                  </>
                )}
              </button>

              <button
                type="button"
                disabled={isVerifying}
                onClick={handleVerify}
                title="Verify live DNS propagation and platform handshake"
                className="flex items-center justify-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-3 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-700 transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">Verify Live DNS</span>
              </button>
            </div>

            <p className="text-center text-[11px] text-slate-400">
              Explicit approval required. DNS changes are executed directly via Cloudflare API and verified in live internet DNS.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
