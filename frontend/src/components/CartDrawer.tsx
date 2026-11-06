import React, { useState } from 'react';
import {
  X,
  Trash2,
  ShoppingCart,
  Shield,
  CheckCircle2,
  ExternalLink,
  Send,
} from 'lucide-react';
import type { CartItem } from '../types/domain';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: CartItem[];
  onRemoveItem: (domain: string) => void;
  onUpdateYears: (domain: string, years: number) => void;
  onUpdateTarget: (domain: string, target: 'vercel' | 'render' | 'none') => void;
  onClearCart: () => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  isOpen,
  onClose,
  items,
  onRemoveItem,
  onUpdateYears,
  onUpdateTarget,
  onClearCart,
}) => {
  const [requestSubmitted, setRequestSubmitted] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  if (!isOpen) return null;

  const total = items.reduce(
    (sum, item) => sum + item.price.registration * item.years,
    0
  );

  const handleSubmitRequest = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      setRequestSubmitted(true);
    }, 1000);
  };

  const handleFinish = () => {
    setRequestSubmitted(false);
    onClearCart();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div className="w-screen max-w-md bg-[#0a0f1d] border-l border-slate-800 p-6 flex flex-col justify-between shadow-2xl">
          {/* Header */}
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600/20 border border-emerald-500/30 text-emerald-400">
                  <ShoppingCart className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">.GY Registration Queue</h2>
                  <p className="text-xs text-slate-400">
                    {items.length} {items.length === 1 ? 'domain' : 'domains'} selected
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Registry Info Notice */}
            <div className="mt-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 text-[11px] text-emerald-300 flex items-center justify-between">
              <span>University of Guyana .GY Registry</span>
              <a
                href="https://registry.gy/registrars/"
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[10px] bg-emerald-500/20 hover:bg-emerald-500/30 px-1.5 py-0.5 rounded text-emerald-200 flex items-center gap-1"
              >
                <span>Accredited Directory</span>
                <ExternalLink className="h-2.5 w-2.5" />
              </a>
            </div>
          </div>

          {/* Cart Content or Success State */}
          <div className="my-6 flex-1 overflow-y-auto space-y-4">
            {requestSubmitted ? (
              <div className="text-center py-6 space-y-4">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
                  <CheckCircle2 className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-bold text-white">
                  Registration Request Queued!
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed max-w-xs mx-auto">
                  No payment was charged. MasterTools coordinates directly with accredited .GY registrars to fulfill official registration. Your Cloudflare DNS and Vercel/Render bridge will link automatically once verified.
                </p>

                <div className="rounded-xl border border-slate-800 bg-[#070b14] p-4 text-left space-y-2 text-xs font-mono">
                  <div className="text-slate-400 text-[11px] uppercase tracking-wider font-semibold">
                    Requested .GY Domains:
                  </div>
                  {items.map((it) => (
                    <div key={it.domain} className="flex items-center justify-between text-emerald-300">
                      <span>{it.domain}</span>
                      <span className="text-slate-400 text-[11px]">
                        {it.connectTarget !== 'none' ? `Cloudflare → ${it.connectTarget}` : 'Awaiting Registrar'}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3 text-left text-xs text-slate-300 space-y-1">
                  <div className="font-semibold text-emerald-300">Official Registry Directory:</div>
                  <p className="text-[11px] text-slate-400">
                    You can also inspect the full list of authorized registrars at{' '}
                    <a
                      href="https://registry.gy/registrars/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-400 underline"
                    >
                      registry.gy/registrars
                    </a>.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleFinish}
                  className="w-full rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 py-3 text-sm font-semibold text-white shadow-lg cursor-pointer hover:brightness-110"
                >
                  Done & Continue Browsing
                </button>
              </div>
            ) : items.length === 0 ? (
              <div className="text-center py-12 space-y-3">
                <ShoppingCart className="mx-auto h-10 w-10 text-slate-600" />
                <p className="text-sm text-slate-400">Your .gy registration queue is empty.</p>
                <p className="text-xs text-slate-400">
                  Search for a name above (e.g. "tala", "prem") and click "Register via Partner".
                </p>
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.domain}
                  className="rounded-xl border border-slate-800 bg-[#0e1629] p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-base font-bold text-white font-mono flex items-center gap-2">
                        <span>{item.domain}</span>
                        <span className="text-[10px] bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 px-1.5 py-0.5 rounded">
                          .gy ccTLD
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                        <span className="flex items-center gap-1 text-emerald-400">
                          <Shield className="h-3 w-3" /> Free Privacy
                        </span>
                        <span>•</span>
                        <span>${item.price.registration.toFixed(2)}/yr standard rate</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => onRemoveItem(item.domain)}
                      className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                      aria-label="Remove item"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Options: Duration & Cloud Connect */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-xs">
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">
                        Registration Term
                      </label>
                      <select
                        value={item.years}
                        onChange={(e) =>
                          onUpdateYears(item.domain, parseInt(e.target.value, 10))
                        }
                        className="w-full rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-xs text-slate-200 focus:outline-none"
                      >
                        <option value={1}>1 Year (${item.price.registration.toFixed(2)})</option>
                        <option value={2}>2 Years (${(item.price.registration * 2).toFixed(2)})</option>
                        <option value={3}>3 Years (${(item.price.registration * 3).toFixed(2)})</option>
                        <option value={5}>5 Years (${(item.price.registration * 5).toFixed(2)})</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">
                        Cloudflare DNS Preset
                      </label>
                      <select
                        value={item.connectTarget || 'none'}
                        onChange={(e) =>
                          onUpdateTarget(
                            item.domain,
                            e.target.value as 'vercel' | 'render' | 'none'
                          )
                        }
                        className="w-full rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-xs text-slate-200 focus:outline-none"
                      >
                        <option value="none">Standard Cloudflare DNS</option>
                        <option value="vercel">⚡ Vercel Edge Bridge</option>
                        <option value="render">⚡ Render Service Bridge</option>
                      </select>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer & Submit button */}
          {!requestSubmitted && items.length > 0 && (
            <div className="pt-4 border-t border-slate-800 space-y-3">
              <div className="space-y-1.5 text-xs text-slate-300">
                <div className="flex justify-between">
                  <span>Estimated Registrar Fee</span>
                  <span className="font-mono">${total.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>WHOIS Privacy & Cloudflare DNS</span>
                  <span className="text-emerald-400 font-semibold">$0.00 (FREE)</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>ICANN Fees</span>
                  <span className="text-slate-400 font-mono">$0.00 (Exempt ccTLD)</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-slate-800 text-sm font-bold text-white">
                  <span>Estimated Total</span>
                  <span className="text-lg font-mono text-emerald-400">
                    ${total.toFixed(2)}
                  </span>
                </div>
              </div>

              <button
                type="button"
                disabled={isProcessing}
                onClick={handleSubmitRequest}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-600/30 hover:brightness-110 active:scale-[0.99] transition-all disabled:opacity-50 cursor-pointer"
              >
                {isProcessing ? (
                  <span>Coordinating with Registrar...</span>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    <span>Submit Registration Request (${total.toFixed(2)})</span>
                  </>
                )}
              </button>

              <p className="text-center text-[11px] text-slate-400 leading-tight">
                No immediate payment required. Registrations are fulfilled through authorized .GY accredited registrars.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
