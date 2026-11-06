import React, { useState, useEffect, useCallback } from 'react';
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
} from 'lucide-react';
import type {
  RegistrationRequestItem,
  RegistrationRequestStatus,
} from '../types/domain';
import {
  listRegistrationRequests,
  updateRegistrationRequest,
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

  useEffect(() => {
    let ignore = false;
    if (isOpen) {
      listRegistrationRequests()
        .then((data) => {
          if (!ignore) {
            setRequests(data.requests);
          }
        })
        .catch(() => {
          if (!ignore) {
            setFeedbackMessage({ type: 'error', text: 'Failed to load registration requests from server.' });
          }
        });
    }
    return () => {
      ignore = true;
    };
  }, [isOpen]);

  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await listRegistrationRequests();
      setRequests(data.requests);
      if (selectedRequest) {
        const found = data.requests.find((r) => r.request_id === selectedRequest.request_id);
        if (found) {
          setSelectedRequest(found);
        }
      }
    } catch {
      setFeedbackMessage({ type: 'error', text: 'Failed to load registration requests from server.' });
    } finally {
      setIsLoading(false);
    }
  }, [selectedRequest]);

  if (!isOpen) return null;

  const handleSelectRequest = (item: RegistrationRequestItem) => {
    setSelectedRequest(item);
    setEditStatus(item.status);
    setEditNotes(item.admin_notes || '');
    setEditConfirmedPrice(item.confirmed_price !== null && item.confirmed_price !== undefined ? item.confirmed_price.toString() : '');
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

    try {
      const updated = await updateRegistrationRequest(selectedRequest.request_id, {
        status: editStatus,
        admin_notes: editNotes.trim() || undefined,
        confirmed_price: priceNum,
      });

      setSelectedRequest(updated);
      setRequests((prev) =>
        prev.map((r) => (r.request_id === updated.request_id ? updated : r))
      );
      setFeedbackMessage({ type: 'success', text: `Request ${updated.request_id} updated successfully.` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update request.';
      setFeedbackMessage({ type: 'error', text: msg });
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
        r.customer_name.toLowerCase().includes(q) ||
        r.customer_email.toLowerCase().includes(q) ||
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
                  .GY Registry Operations & Admin Portal
                </span>
                <span className="rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 text-[10px] font-mono font-bold">
                  Internal
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Manage customer .gy manual registration inquiries and registrar coordination
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:text-white hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

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
                          <span>Est: ${item.estimated_annual_price.toFixed(2)}/yr</span>
                          {item.confirmed_price && (
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
                      .GY ccTLD
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
                      <span className="text-[10px] text-slate-500">
                        Est: ${selectedRequest.estimated_annual_price.toFixed(2)}/yr
                      </span>
                    </div>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={editConfirmedPrice}
                      onChange={(e) => setEditConfirmedPrice(e.target.value)}
                      placeholder="e.g. 45.00"
                      className="w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2 text-xs sm:text-sm font-mono text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                    <span className="text-[10px] text-slate-500 mt-1 block">
                      Leave empty until exact price is confirmed with the accredited registrar.
                    </span>
                  </div>

                  {/* Internal Admin Notes */}
                  <div>
                    <label className="text-xs text-slate-400 block mb-1.5">
                      Internal Admin Notes
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
      </div>
    </div>
  );
};
