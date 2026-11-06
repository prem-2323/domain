import React, { useState } from 'react';
import {
  X,
  Send,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  Shield,
  Loader2,
  ExternalLink,
  Info,
} from 'lucide-react';
import type { DomainSearchResult, RegistrationRequestItem } from '../types/domain';
import { submitRegistrationRequest, RegistrationApiError } from '../api/domainService';

interface RegistrationRequestModalProps {
  domainItem: DomainSearchResult | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (request: RegistrationRequestItem) => void;
}

export const RegistrationRequestModal: React.FC<RegistrationRequestModalProps> = ({
  domainItem,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [createdRequest, setCreatedRequest] = useState<RegistrationRequestItem | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  if (!isOpen || !domainItem) return null;

  const targetDomain = domainItem.domain;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const name = customerName.trim();
    const email = customerEmail.trim();

    if (!name || name.length < 2) {
      setErrorMessage('Please enter your full name (at least 2 characters).');
      return;
    }

    if (!email || !email.includes('@') || !email.includes('.')) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await submitRegistrationRequest({
        customer_name: name,
        customer_email: email,
        domain: targetDomain,
        message: message.trim() || undefined,
      });

      setCreatedRequest(response);
      if (onSuccess) {
        onSuccess(response);
      }
    } catch (err: unknown) {
      if (err instanceof RegistrationApiError) {
        setErrorMessage(err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('An unexpected error occurred while submitting your request.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleCopyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    setCopiedToken(true);
    setTimeout(() => setCopiedToken(false), 2000);
  };

  const handleResetAndClose = () => {
    setCustomerName('');
    setCustomerEmail('');
    setMessage('');
    setErrorMessage(null);
    setCreatedRequest(null);
    setCopiedId(false);
    setCopiedToken(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
        onClick={handleResetAndClose}
      />

      <div className="relative w-full max-w-lg rounded-3xl border border-slate-800 bg-[#0c1222] p-6 sm:p-7 shadow-2xl z-10 my-8">
        {/* Close Button */}
        <button
          type="button"
          onClick={handleResetAndClose}
          className="absolute top-5 right-5 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          aria-label="Close modal"
        >
          <X className="h-5 w-5" />
        </button>

        {createdRequest ? (
          /* Confirmation State with Unique Request ID */
          <div className="text-center space-y-4 py-2">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400">
              <CheckCircle2 className="h-9 w-9" />
            </div>

            <div>
              <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-1 text-xs font-bold text-emerald-300 uppercase tracking-wider">
                Request Submitted
              </span>
              <h2 className="text-2xl font-bold text-white mt-2 font-mono">
                {createdRequest.domain}
              </h2>
            </div>

            {/* Request ID Display */}
            <div className="rounded-2xl border border-slate-800 bg-[#070b14] p-4 text-left space-y-2">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
                Your Unique Request ID (128-Bit Cryptographic ID):
              </div>
              <div className="flex items-center justify-between gap-2 rounded-xl bg-slate-900 border border-slate-700/80 px-3 py-2 font-mono text-sm text-emerald-400 font-bold">
                <span className="truncate">{createdRequest.request_id}</span>
                <button
                  type="button"
                  onClick={() => handleCopyId(createdRequest.request_id)}
                  className="flex items-center gap-1 text-xs font-sans text-slate-300 hover:text-white bg-slate-800 px-2 py-1 rounded transition-colors shrink-0"
                >
                  {copiedId ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy ID</span>
                    </>
                  )}
                </button>
              </div>
              <div className="text-xs text-slate-400 pt-1">
                Save this request ID to reference your inquiry. Public tracking displays status without exposing your private info.
              </div>
            </div>

            {/* Customer Private Tracking Token */}
            {createdRequest.tracking_token && (
              <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/20 p-4 text-left space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-[11px] text-indigo-300 uppercase tracking-wider font-semibold">
                    Private Customer Tracking Token:
                  </div>
                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded font-mono">
                    Keep Secret
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2 rounded-xl bg-slate-900 border border-indigo-500/40 px-3 py-2 font-mono text-xs text-indigo-300">
                  <span className="truncate max-w-[280px]">{createdRequest.tracking_token}</span>
                  <button
                    type="button"
                    onClick={() => handleCopyToken(createdRequest.tracking_token!)}
                    className="flex items-center gap-1 text-xs font-sans text-slate-300 hover:text-white bg-slate-800 px-2 py-1 rounded transition-colors shrink-0"
                  >
                    {copiedToken ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy Token</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="text-[11px] text-slate-400">
                  This token allows you to securely verify and view your customer submission without exposing your contact details publicly.
                </div>
              </div>
            )}

            {/* Request Summary */}
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-3.5 text-left text-xs space-y-1.5">
              <div className="flex justify-between text-slate-300">
                <span className="text-slate-400">Customer Name:</span>
                <span className="font-medium text-white">{createdRequest.customer_name}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span className="text-slate-400">Customer Email:</span>
                <span className="font-mono text-slate-200">{createdRequest.customer_email}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span className="text-slate-400">Current Status:</span>
                <span className="text-amber-300 font-semibold">{createdRequest.status_label}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span className="text-slate-400">Estimated Rate:</span>
                <span className="font-mono text-emerald-400 font-bold">~${createdRequest.estimated_annual_price.toFixed(2)}/yr (Estimate)</span>
              </div>
            </div>

            {/* Disclaimer Reminder */}
            <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 text-left text-[11px] text-amber-200/90 flex items-start gap-2">
              <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              <span>
                <strong>Next Steps:</strong> An accredited registrar liaison will verify registry availability directly with the University of Guyana .GY Registry. We will email you at <strong>{createdRequest.customer_email}</strong> with confirmed pricing before any registration is completed.
              </span>
            </div>

            <button
              type="button"
              onClick={handleResetAndClose}
              className="w-full rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-600/30 hover:brightness-110 active:scale-[0.99] transition-all cursor-pointer"
            >
              Done & Return to Search
            </button>
          </div>
        ) : (
          /* Submission Form */
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-600/30">
                <Send className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                    Manual Registration Request
                  </span>
                  <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                    .GY ccTLD
                  </span>
                </div>
                <h2 className="text-xl font-bold text-white font-mono flex items-center gap-1.5">
                  <span>Request</span>
                  <span className="text-emerald-400 font-extrabold">{targetDomain}</span>
                </h2>
              </div>
            </div>

            {/* Strict Regulatory Disclaimer Alert */}
            <div className="mb-5 rounded-2xl border border-amber-500/30 bg-gradient-to-b from-amber-950/30 to-amber-950/10 p-4 text-xs text-amber-200/90 space-y-1.5">
              <div className="flex items-center gap-1.5 font-bold text-amber-300">
                <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
                <span>Notice on .GY Domain Allocation</span>
              </div>
              <p className="leading-relaxed text-[11px] text-slate-300">
                Submitting this request <strong>does not register, hold, or reserve</strong> the domain.
                All .gy domains are administered by the University of Guyana .GY Registry and allocated through accredited registrars.
                Our team will verify registry availability and provide confirmed pricing before formal registration occurs.
              </p>
              <div className="pt-1 flex items-center gap-1 text-[11px] text-amber-400">
                <ExternalLink className="h-3 w-3" />
                <a
                  href="https://registry.gy/registrars/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-amber-200"
                >
                  View University of Guyana Accredited Registrars Directory
                </a>
              </div>
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Requested Domain (Read-only / Pre-filled) */}
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1.5">
                  Requested Domain
                </label>
                <div className="flex items-center justify-between rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 font-mono text-sm text-emerald-400 font-semibold">
                  <span>{targetDomain}</span>
                  <span className="text-xs text-slate-400 font-sans font-normal">
                    Est. ~${domainItem.price.registration.toFixed(2)}/yr (Subject to registrar confirmation)
                  </span>
                </div>
              </div>

              {/* Customer Name */}
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1.5">
                  Full Customer Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="e.g. Tala Adams"
                  className="w-full rounded-xl bg-slate-900/90 border border-slate-800 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all"
                />
              </div>

              {/* Customer Email */}
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1.5">
                  Email Address for Coordination <span className="text-rose-400">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  placeholder="e.g. tala@example.com"
                  className="w-full rounded-xl bg-slate-900/90 border border-slate-800 px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all"
                />
                <span className="text-[11px] text-slate-400 mt-1 block">
                  We will send your unique Request ID and registrar availability status here.
                </span>
              </div>

              {/* Optional Message */}
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1.5">
                  Optional Notes / Intended Project
                </label>
                <textarea
                  rows={2}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="e.g. Portfolio site hosted on Vercel; need Cloudflare DNS integration..."
                  className="w-full rounded-xl bg-slate-900/90 border border-slate-800 px-3.5 py-2 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all resize-none"
                />
              </div>

              {/* Value Inclusions */}
              <div className="flex items-center gap-2 text-xs text-slate-400 pt-1">
                <Shield className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                <span>Zero payment required today • Handled via accredited registrar partners</span>
              </div>

              {/* Submit CTA */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-600/30 hover:brightness-110 active:scale-[0.99] transition-all disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Submitting Request...</span>
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      <span>Submit Registration Request</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
