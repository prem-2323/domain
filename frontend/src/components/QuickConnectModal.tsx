import React, { useState } from 'react';
import {
  X,
  Server,
  Zap,
  CheckCircle2,
  Copy,
  Check,
  ShieldCheck,
} from 'lucide-react';
import type { DomainSearchResult } from '../types/domain';

interface QuickConnectModalProps {
  domainItem: DomainSearchResult | null;
  onClose: () => void;
}

export const QuickConnectModal: React.FC<QuickConnectModalProps> = ({
  domainItem,
  onClose,
}) => {
  const [target, setTarget] = useState<'vercel' | 'render'>('vercel');
  const [isApplied, setIsApplied] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!domainItem) return null;

  const domain = domainItem.domain;

  const vercelRecords = [
    { type: 'A', name: '@', value: '76.76.21.21', purpose: 'Root apex routing' },
    { type: 'CNAME', name: 'www', value: 'cname.vercel-dns.com', purpose: 'Wildcard & www subdomain' },
  ];

  const renderRecords = [
    { type: 'ALIAS', name: '@', value: `${domainItem.name}-app.onrender.com`, purpose: 'Apex CNAME flattening' },
    { type: 'CNAME', name: 'www', value: `${domainItem.name}-app.onrender.com`, purpose: 'Render Web Service endpoint' },
  ];

  const records = target === 'vercel' ? vercelRecords : renderRecords;

  const handleApply = () => {
    setIsApplied(true);
  };

  const handleCopyAll = () => {
    const text = records
      .map((r) => `${r.type}\t${r.name}\t${r.value}`)
      .join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="relative w-full max-w-xl rounded-3xl border border-slate-800 bg-[#0c1222] p-6 sm:p-7 shadow-2xl z-10">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-5 right-5 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-lg shadow-indigo-600/30">
            <Server className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                Cloudflare Edge Bridge
              </span>
              <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                Anycast DNS
              </span>
            </div>
            <h2 className="text-xl font-bold text-white font-mono flex items-center gap-1.5">
              <span>Connect</span>
              <span className="text-emerald-400 font-extrabold">{domain}</span>
            </h2>
          </div>
        </div>

        {/* Target Switcher */}
        <div className="mb-5">
          <label className="text-xs text-slate-400 block mb-2 font-medium">
            Select Cloud Destination:
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setTarget('vercel');
                setIsApplied(false);
              }}
              className={`flex items-center gap-2.5 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                target === 'vercel'
                  ? 'border-indigo-500 bg-indigo-950/30 ring-1 ring-indigo-500/50'
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
              onClick={() => {
                setTarget('render');
                setIsApplied(false);
              }}
              className={`flex items-center gap-2.5 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                target === 'render'
                  ? 'border-emerald-500 bg-emerald-950/30 ring-1 ring-emerald-500/50'
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

        {/* DNS Configuration Preview Box */}
        <div className="rounded-2xl border border-slate-800 bg-[#080d19] p-4 mb-5">
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-800 text-xs">
            <span className="font-semibold text-slate-300">
              Generated {target === 'vercel' ? 'Vercel' : 'Render'} Records
            </span>
            <button
              type="button"
              onClick={handleCopyAll}
              className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
              <span>{copied ? 'Copied!' : 'Copy Records'}</span>
            </button>
          </div>

          <div className="space-y-2 text-xs font-mono">
            {records.map((r, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg bg-slate-900/90 border border-slate-800/80 p-2 text-slate-300"
              >
                <div className="flex items-center gap-2">
                  <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-indigo-300 font-bold text-[10px]">
                    {r.type}
                  </span>
                  <span className="text-white font-semibold">{r.name}</span>
                  <span className="text-slate-400">→</span>
                  <span className="text-slate-300 truncate max-w-[180px]">{r.value}</span>
                </div>
                <span className="text-[10px] text-slate-400 font-sans">{r.purpose}</span>
              </div>
            ))}
          </div>

          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-slate-400">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Automatic Let's Encrypt SSL certificate issuance upon propagation</span>
          </div>
        </div>

        {/* Action Button & Status */}
        {isApplied ? (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-center space-y-2">
            <div className="flex items-center justify-center gap-2 text-emerald-400 font-semibold text-sm">
              <CheckCircle2 className="h-4 w-4" />
              <span>DNS Records Pre-Configured!</span>
            </div>
            <p className="text-xs text-slate-300">
              Add <strong>{domain}</strong> in your {target === 'vercel' ? 'Vercel Project Settings > Domains' : 'Render Service > Custom Domains'}. It will verify instantly.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="mt-2 w-full rounded-xl bg-slate-800 border border-slate-700 py-2 text-xs font-semibold text-white hover:bg-slate-700 cursor-pointer"
            >
              Done
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <button
              type="button"
              onClick={handleApply}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 hover:brightness-110 active:scale-[0.99] transition-all cursor-pointer"
            >
              <Zap className="h-4 w-4" />
              <span>Auto-Provision {target === 'vercel' ? 'Vercel' : 'Render'} DNS</span>
            </button>
            <p className="text-center text-[11px] text-slate-400">
              Applies zero-touch Anycast DNS routing for this domain.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
