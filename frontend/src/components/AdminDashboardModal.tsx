import React, { useState, useEffect } from 'react';
import {
  X,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  ShieldAlert,
  Save,
  Loader2,
  ExternalLink,
  ChevronRight,
  Lock,
  LogOut,
  User,
  Key,
  ShieldCheck,
} from 'lucide-react';
import type {
  RegistrationRequestItem,
  RegistrationRequestStatus,
} from '../types/domain';
import {
  listRegistrationRequests,
  updateRegistrationRequest,
  adminLogin,
  adminLogout,
  checkAdminSession,
  RegistrationApiError,
} from '../api/domainService';

interface AdminDashboardModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const STATUS_CONFIG: Record<
  RegistrationRequestStatus,
  { label: string; bg: string; text: string; border: string; icon: React.FC<{ className?: string }> }
> = {
  pending: {
    label: 'Pending Initial Review',
    bg: 'bg-amber-500/15',
    text: 'text-amber-300',
    border: 'border-amber-500/30',
    icon: Clock,
  },
  verification_required: {
    label: 'Verification Required',
    bg: 'bg-blue-500/15',
    text: 'text-blue-300',
    border: 'border-blue-500/30',
    icon: AlertTriangle,
  },
  verified_available: {
    label: 'Verified Available',
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-300',
    border: 'border-emerald-500/30',
    icon: CheckCircle2,
  },
  unavailable: {
    label: 'Unavailable / Reserved',
    bg: 'bg-rose-500/15',
    text: 'text-rose-300',
    border: 'border-rose-500/30',
    icon: XCircle,
  },
  registration_in_progress: {
    label: 'Registration in Progress',
    bg: 'bg-purple-500/15',
    text: 'text-purple-300',
    border: 'border-purple-500/30',
    icon: Clock,
  },
  registered: {
    label: 'Registration Confirmed',
    bg: 'bg-emerald-600/20',
    text: 'text-emerald-400 font-bold',
    border: 'border-emerald-500/40',
    icon: CheckCircle2,
  },
  rejected: {
    label: 'Rejected',
    bg: 'bg-slate-700/30',
    text: 'text-slate-400',
    border: 'border-slate-700',
    icon: XCircle,
  },
};

export const AdminDashboardModal: React.FC<AdminDashboardModalProps> = ({
  isOpen,
  onClose,
}) => {
  // Authentication states
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [adminUsername, setAdminUsername] = useState<string>('');
  const [isCheckingAuth, setIsCheckingAuth] = useState<boolean>(true);
  const [loginUsername, setLoginUsername] = useState<string>('');
  const [loginPassword, setLoginPassword] = useState<string>('');
  const [isLoggingIn, setIsLoggingIn] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Request list and editor states
  const [requests, setRequests] = useState<RegistrationRequestItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<RegistrationRequestItem | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Editable fields for selected request
  const [editStatus, setEditStatus] = useState<RegistrationRequestStatus>('pending');
  const [editNotes, setEditNotes] = useState<string>('');
  const [editConfirmedPrice, setEditConfirmedPrice] = useState<string>('');
  const [editConfirmationRef, setEditConfirmationRef] = useState<string>('');

  // Check auth session on modal open
  useEffect(() => {
    let ignore = false;
    if (!isOpen) return;

    checkAdminSession()
      .then(async (session) => {
        if (ignore) return;
        setIsAuthenticated(session.authenticated);
        setAdminUsername(session.username);
        setIsCheckingAuth(false);
        if (session.authenticated) {
          const data = await listRegistrationRequests().catch(() => null);
          if (!ignore && data) {
            setRequests(data.requests);
          }
        }
      })
      .catch(() => {
        if (!ignore) {
          setIsAuthenticated(false);
          setIsCheckingAuth(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [isOpen]);

  const loadRequests = async () => {
    setIsLoading(true);
    setFeedbackMessage(null);
    try {
      const data = await listRegistrationRequests();
      setRequests(data.requests);
      if (selectedRequest) {
        const found = data.requests.find((r) => r.request_id === selectedRequest.request_id);
        if (found) {
          setSelectedRequest(found);
        }
      }
    } catch (err) {
      if (err instanceof RegistrationApiError && err.status === 401) {
        setIsAuthenticated(false);
        setLoginError('Session expired. Please sign in again.');
      } else {
        setFeedbackMessage({ type: 'error', text: 'Failed to load registration requests from server.' });
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginUsername.trim() || !loginPassword.trim()) {
      setLoginError('Please enter both username and password.');
      return;
    }

    setIsLoggingIn(true);
    setLoginError(null);

    try {
      const res = await adminLogin(loginUsername.trim(), loginPassword);
      setIsAuthenticated(true);
      setAdminUsername(res.username);
      setLoginPassword('');
      // Load requests immediately
      const data = await listRegistrationRequests();
      setRequests(data.requests);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Invalid administrator username or password.';
      setLoginError(msg);
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = async () => {
    await adminLogout();
    setIsAuthenticated(false);
    setAdminUsername('');
    setRequests([]);
    setSelectedRequest(null);
    setFeedbackMessage(null);
  };

  const handleSelectRequest = (item: RegistrationRequestItem) => {
    setSelectedRequest(item);
    setEditStatus(item.status);
    setEditNotes(item.admin_notes || '');
    setEditConfirmedPrice(item.confirmed_price !== null && item.confirmed_price !== undefined ? item.confirmed_price.toString() : '');
    setEditConfirmationRef(item.confirmation_reference || '');
    setFeedbackMessage(null);
  };

  const handleSaveUpdates = async () => {
    if (!selectedRequest) return;
    setIsSaving(true);
    setFeedbackMessage(null);

    const priceNum = editConfirmedPrice.trim() ? parseFloat(editConfirmedPrice) : undefined;
    if (editConfirmedPrice.trim() && (isNaN(priceNum!) || priceNum! < 0)) {
      setFeedbackMessage({ type: 'error', text: 'Confirmed price must be a valid positive number.' });
      setIsSaving(false);
      return;
    }

    // Enforce status integrity: registered status requires reference and notes
    if (editStatus === 'registered') {
      if (!editConfirmationRef.trim() || editConfirmationRef.trim().length < 3) {
        setFeedbackMessage({
          type: 'error',
          text: 'Policy requirement: Official accredited registrar confirmation reference (min 3 chars) is mandatory to confirm registration.',
        });
        setIsSaving(false);
        return;
      }
      if (!editNotes.trim() || editNotes.trim().length < 10) {
        setFeedbackMessage({
          type: 'error',
          text: 'Policy requirement: Internal admin notes explaining registry verification (min 10 chars) are mandatory to confirm registration.',
        });
        setIsSaving(false);
        return;
      }
    }

    try {
      const updated = await updateRegistrationRequest(selectedRequest.request_id, {
        status: editStatus,
        admin_notes: editNotes.trim() || undefined,
        confirmed_price: priceNum,
        confirmation_reference: editConfirmationRef.trim() || undefined,
      });

      setSelectedRequest(updated);
      setRequests((prev) =>
        prev.map((r) => (r.request_id === updated.request_id ? updated : r))
      );
      setFeedbackMessage({ type: 'success', text: `Request ${updated.request_id} updated successfully.` });
    } catch (err: unknown) {
      if (err instanceof RegistrationApiError && err.status === 401) {
        setIsAuthenticated(false);
        setLoginError('Session expired. Please sign in again.');
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to update request.';
        setFeedbackMessage({ type: 'error', text: msg });
      }
    } finally {
      setIsSaving(false);
    }
  };

  // Filter and search
  const filteredRequests = requests.filter((r) => {
    if (statusFilter !== 'all' && r.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      return (
        r.domain.toLowerCase().includes(q) ||
        (r.customer_name && r.customer_name.toLowerCase().includes(q)) ||
        (r.customer_email && r.customer_email.toLowerCase().includes(q)) ||
        r.request_id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  // KPI counts
  const pendingCount = requests.filter((r) => r.status === 'pending').length;
  const inProgressCount = requests.filter((r) => r.status === 'registration_in_progress').length;
  const verifiedCount = requests.filter((r) => r.status === 'verified_available').length;
  const registeredCount = requests.filter((r) => r.status === 'registered').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />

      <div className="relative w-full max-w-6xl h-[90vh] rounded-3xl border border-slate-800 bg-[#090d18] shadow-2xl z-10 flex flex-col overflow-hidden">
        {/* Top Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0c1222]">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-white">
                  Registry Operations & Admin Portal
                </span>
                <span className="rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                  FREE TESTING MODE ACTIVE
                </span>
                <span className="rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 text-[10px] font-mono font-bold">
                  Restricted
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Manage customer multi-TLD registration inquiries and registrar coordination ($0 Free Testing Mode)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isAuthenticated && (
              <>
                <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="font-mono text-slate-400">Admin:</span>
                  <span className="font-semibold text-white">{adminUsername}</span>
                </div>
                <button
                  type="button"
                  onClick={loadRequests}
                  disabled={isLoading}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white hover:bg-slate-700 transition-colors"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-950/30 px-3 py-1.5 text-xs font-medium text-rose-300 hover:text-white hover:bg-rose-900/50 transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Close modal"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Loading Auth State */}
        {isCheckingAuth ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
            <span className="text-xs text-slate-400">Verifying administrator authorization...</span>
          </div>
        ) : !isAuthenticated ? (
          /* Admin Login Gate */
          <div className="flex-1 flex items-center justify-center p-6 bg-[#080c16]">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d1322] p-7 shadow-2xl space-y-5">
              <div className="text-center space-y-2">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                  <Lock className="h-7 w-7" />
                </div>
                <h3 className="text-xl font-bold text-white">Administrator Access Required</h3>
                <p className="text-xs text-slate-400">
                  This portal is protected. Only authenticated registry operators can access customer registration requests, update workflow statuses, and submit registrar references.
                </p>
              </div>

              {loginError && (
                <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300 flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                  <span>{loginError}</span>
                </div>
              )}

              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div>
                  <label className="text-xs text-slate-300 font-medium block mb-1.5">
                    Admin Username
                  </label>
                  <div className="relative">
                    <User className="h-4 w-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      required
                      value={loginUsername}
                      onChange={(e) => setLoginUsername(e.target.value)}
                      placeholder="admin"
                      className="w-full rounded-xl bg-slate-900 border border-slate-700 pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-300 font-medium block mb-1.5">
                    Admin Password
                  </label>
                  <div className="relative">
                    <Key className="h-4 w-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="password"
                      required
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full rounded-xl bg-slate-900 border border-slate-700 pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoggingIn}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 py-2.5 text-sm font-semibold text-white shadow-lg hover:brightness-110 active:scale-[0.99] transition-all cursor-pointer disabled:opacity-50"
                >
                  {isLoggingIn ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Authenticating...</span>
                    </>
                  ) : (
                    <>
                      <Lock className="h-4 w-4" />
                      <span>Sign In to Registry Operations</span>
                    </>
                  )}
                </button>
              </form>

              <div className="pt-2 border-t border-slate-800 text-center">
                <span className="text-[11px] text-slate-500">
                  Protected with HMAC-SHA256 session authentication & SQLite session management.
                </span>
              </div>
            </div>
          </div>
        ) : (
          /* Authenticated Dashboard Content */
          <>
            {/* Quick Stats Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 px-6 py-3 border-b border-slate-800/80 bg-[#070b14] text-xs">
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Total Requests:</span>
                <span className="font-bold text-white font-mono">{requests.length}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-amber-950/20 border border-amber-500/20">
                <span className="text-amber-400">Pending Review:</span>
                <span className="font-bold text-amber-300 font-mono">{pendingCount}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-950/20 border border-emerald-500/20">
                <span className="text-emerald-400">Verified Available:</span>
                <span className="font-bold text-emerald-300 font-mono">{verifiedCount}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-purple-950/20 border border-purple-500/20">
                <span className="text-purple-400">In Progress:</span>
                <span className="font-bold text-purple-300 font-mono">{inProgressCount}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-950/30 border border-emerald-500/30 col-span-2 sm:col-span-1">
                <span className="text-emerald-300">Registered:</span>
                <span className="font-bold text-emerald-300 font-mono">{registeredCount}</span>
              </div>
            </div>

            {/* Main Content: Split Master-Detail */}
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
              {/* Left Column: Request List */}
              <div className="w-full md:w-7/12 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col overflow-hidden">
                {/* Search and Filters */}
                <div className="p-4 border-b border-slate-800/80 space-y-3 bg-[#0a0f1d]">
                  <div className="relative">
                    <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search by domain, name, email, or request ID..."
                      className="w-full rounded-xl bg-slate-900 border border-slate-800 pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  {/* Status Filter Chips */}
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px]">
                    <span className="text-slate-400 flex items-center gap-1 shrink-0">
                      <Filter className="h-3 w-3" /> Status:
                    </span>
                    {[
                      { id: 'all', label: 'All' },
                      { id: 'pending', label: 'Pending' },
                      { id: 'verification_required', label: 'Verify' },
                      { id: 'verified_available', label: 'Available' },
                      { id: 'registration_in_progress', label: 'In Progress' },
                      { id: 'registered', label: 'Registered' },
                      { id: 'unavailable', label: 'Unavailable' },
                      { id: 'rejected', label: 'Rejected' },
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setStatusFilter(tab.id)}
                        className={`rounded-lg px-2.5 py-1 whitespace-nowrap font-medium transition-all cursor-pointer ${
                          statusFilter === tab.id
                            ? 'bg-indigo-600 text-white font-semibold'
                            : 'text-slate-400 hover:text-white hover:bg-slate-800'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* List Items */}
                <div className="flex-1 overflow-y-auto divide-y divide-slate-800/80 p-2 space-y-1">
                  {filteredRequests.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No registration requests match the selected criteria.
                    </div>
                  ) : (
                    filteredRequests.map((item) => {
                      const isSelected = selectedRequest?.request_id === item.request_id;
                      const cfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
                      const StatusIcon = cfg.icon;

                      return (
                        <div
                          key={item.request_id}
                          onClick={() => handleSelectRequest(item)}
                          className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                            isSelected
                              ? 'border-indigo-500 bg-indigo-950/30 ring-1 ring-indigo-500/40'
                              : 'border-transparent hover:border-slate-800 hover:bg-slate-900/60'
                          }`}
                        >
                          <div className="space-y-1 min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm font-bold text-white">
                                {item.domain}
                              </span>
                              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
                                <StatusIcon className="h-3 w-3" />
                                <span>{cfg.label}</span>
                              </span>
                            </div>

                            <div className="flex items-center gap-3 text-xs text-slate-400">
                              <span className="text-slate-300">{item.customer_name}</span>
                              <span>•</span>
                              <span className="font-mono text-[11px] truncate">{item.customer_email}</span>
                            </div>

                            <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono">
                              <span>{item.request_id}</span>
                              <span>•</span>
                              <span className="text-emerald-400 font-semibold">$0.00 (Free Testing)</span>
                              {item.confirmed_price !== null && item.confirmed_price !== undefined && (
                                <>
                                  <span>•</span>
                                  <span className="text-emerald-400 font-semibold">
                                    Confirmed: ${item.confirmed_price.toFixed(2)}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>

                          <ChevronRight className="h-4 w-4 text-slate-600 shrink-0" />
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Right Column: Detail & Edit Panel */}
              <div className="w-full md:w-5/12 bg-[#0b101f] p-5 flex flex-col justify-between overflow-y-auto">
                {selectedRequest ? (
                  <div className="space-y-5">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs text-indigo-400 font-bold">
                          {selectedRequest.request_id}
                        </span>
                        <span className="text-[11px] text-slate-500">
                          Submitted: {new Date(selectedRequest.created_at).toLocaleString()}
                        </span>
                      </div>
                      <h3 className="text-2xl font-bold font-mono text-white flex items-center gap-2">
                        <span>{selectedRequest.domain}</span>
                        <span className="text-xs bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 px-2 py-0.5 rounded font-sans font-medium">
                          {selectedRequest.domain.slice(selectedRequest.domain.indexOf('.')) || 'TLD'}
                        </span>
                      </h3>
                    </div>

                    {/* Customer Details Box */}
                    <div className="rounded-xl border border-slate-800 bg-[#070b14] p-3.5 space-y-2 text-xs">
                      <div className="font-semibold text-slate-300 text-[11px] uppercase tracking-wider">
                        Customer Information
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-slate-300">
                        <div>
                          <span className="text-slate-500 block text-[10px]">Name</span>
                          <span className="font-medium text-white">{selectedRequest.customer_name}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[10px]">Email</span>
                          <span className="font-mono text-slate-200 truncate block">
                            {selectedRequest.customer_email}
                          </span>
                        </div>
                      </div>
                      {selectedRequest.message && (
                        <div className="pt-2 border-t border-slate-800/80">
                          <span className="text-slate-500 block text-[10px]">Customer Message:</span>
                          <p className="text-slate-300 italic text-xs mt-0.5">
                            "{selectedRequest.message}"
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Official Registry Directory Link */}
                    <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3 text-xs text-emerald-200/90 flex items-center justify-between">
                      <span>University of Guyana .GY Registry</span>
                      <a
                        href="https://registry.gy/registrars/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 font-mono text-[11px] text-emerald-400 underline hover:text-emerald-300"
                      >
                        <span>Check Registrars</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>

                    {/* Feedback Toast */}
                    {feedbackMessage && (
                      <div
                        className={`rounded-xl border p-3 text-xs ${
                          feedbackMessage.type === 'success'
                            ? 'border-emerald-500/30 bg-emerald-950/30 text-emerald-300'
                            : 'border-rose-500/30 bg-rose-950/30 text-rose-300'
                        }`}
                      >
                        {feedbackMessage.text}
                      </div>
                    )}

                    {/* Status Update Controls */}
                    <div className="space-y-4 pt-2 border-t border-slate-800/80">
                      <div className="font-semibold text-white text-sm">
                        Update Request Status & Liaison Notes
                      </div>

                      {/* Status Dropdown */}
                      <div>
                        <label className="text-xs text-slate-400 block mb-1.5">
                          Workflow Status
                        </label>
                        <select
                          value={editStatus}
                          onChange={(e) => setEditStatus(e.target.value as RegistrationRequestStatus)}
                          className="w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2 text-xs sm:text-sm text-white focus:outline-none focus:border-indigo-500"
                        >
                          <option value="pending">pending — Pending Initial Review</option>
                          <option value="verification_required">verification_required — Awaiting .GY Registry Verification</option>
                          <option value="verified_available">verified_available — Confirmed Available by Registrar</option>
                          <option value="registration_in_progress">registration_in_progress — Partner Coordination in Progress</option>
                          <option value="registered">registered — Registration Manually Confirmed</option>
                          <option value="unavailable">unavailable — Unavailable / Reserved in .GY Registry</option>
                          <option value="rejected">rejected — Request Rejected</option>
                        </select>
                      </div>

                      {/* Confirmed Price (Distinguishes estimated from confirmed) */}
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-xs text-slate-400">
                            Confirmed Registrar Price ($ USD)
                          </label>
                          <span className="text-[10px] text-emerald-400 font-semibold">
                            Testing Mode: $0.00
                          </span>
                        </div>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={editConfirmedPrice}
                          onChange={(e) => setEditConfirmedPrice(e.target.value)}
                          placeholder="0.00"
                          className="w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2 text-xs sm:text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                        />
                        <span className="text-[10px] text-slate-500 mt-1 block">
                          Leave empty or 0.00 for free testing mode.
                        </span>
                      </div>

                      {/* Required Confirmation Reference when Registered */}
                      {editStatus === 'registered' && (
                        <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-3 space-y-2">
                          <label className="text-xs font-semibold text-purple-300 block">
                            Accredited Registrar Confirmation Reference / Receipt # <span className="text-rose-400">*</span>
                          </label>
                          <input
                            type="text"
                            required
                            value={editConfirmationRef}
                            onChange={(e) => setEditConfirmationRef(e.target.value)}
                            placeholder="e.g. REG-GY-ACC-9921 or Registry Order #5421"
                            className="w-full rounded-xl bg-slate-900 border border-purple-500/40 px-3 py-2 text-xs sm:text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:border-purple-400"
                          />
                          <span className="text-[10px] text-purple-300/80 block">
                            Required by policy. You must provide the official registrar order, ticket, or reference ID before marking a domain as registered.
                          </span>
                        </div>
                      )}

                      {/* Internal Admin Notes */}
                      <div>
                        <label className="text-xs text-slate-400 block mb-1.5">
                          Internal Admin Notes {editStatus === 'registered' && <span className="text-rose-400">* (min 10 chars)</span>}
                        </label>
                        <textarea
                          rows={3}
                          value={editNotes}
                          onChange={(e) => setEditNotes(e.target.value)}
                          placeholder="e.g. Checked registry.gy; name is available. Contacted accredited registrar for invoice and DNS delegation..."
                          className="w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                        />
                      </div>

                      {/* Warning on Status Integrity */}
                      <div className="rounded-xl border border-amber-500/20 bg-amber-950/15 p-2.5 text-[11px] text-amber-300/80">
                        <strong>Notice:</strong> Never set status to <em>"registered"</em> until the accredited registrar confirms the domain is officially recorded in the University of Guyana Registry.
                      </div>

                      {/* Save Button */}
                      <button
                        type="button"
                        disabled={isSaving}
                        onClick={handleSaveUpdates}
                        className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 py-2.5 text-xs font-semibold text-white shadow-lg hover:brightness-110 active:scale-[0.99] transition-all cursor-pointer disabled:opacity-50"
                      >
                        {isSaving ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span>Saving Changes...</span>
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4" />
                            <span>Save Status & Notes</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center text-slate-500 space-y-2 p-6">
                    <Clock className="h-10 w-10 text-slate-600" />
                    <div className="text-sm font-medium text-slate-400">No Request Selected</div>
                    <p className="text-xs max-w-xs">
                      Select a registration request from the list on the left to review customer details, update status, and manage registrar liaison notes.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
