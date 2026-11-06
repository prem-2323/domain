import type {
  DomainSearchResult,
  DomainAvailability,
  ApiDomainSearchResponse,
  ApiDomainResult,
} from '../types/domain';
import { POPULAR_EXTENSIONS } from '../data/extensionCatalog';

const isProd = import.meta.env.PROD;
const rawApiBase = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL = rawApiBase ? rawApiBase.replace(/\/$/, '') : '';

/**
 * Returns prioritized API endpoint targets.
 * In production: strictly uses configured VITE_API_BASE_URL or relative origin path.
 * Localhost fallback is disabled in production to protect live user traffic.
 */
export function getApiEndpoints(path: string): string[] {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  if (API_BASE_URL) {
    return [`${API_BASE_URL}${cleanPath}`];
  }
  if (!isProd) {
    return [`http://localhost:8000${cleanPath}`];
  }
  return [cleanPath];
}

export interface BackendStatus {
  connected: boolean;
  message?: string;
  service?: string;
}

export class DomainValidationError extends Error {
  public query: string;

  constructor(message: string, query: string) {
    super(message);
    this.name = 'DomainValidationError';
    this.query = query;
  }
}

// Clean and extract name and extension across any TLD (.gy, .com, .in, etc.)
export function parseDomainQuery(rawQuery: string): { name: string; explicitTld: string } {
  let cleaned = rawQuery.trim().toLowerCase();
  cleaned = cleaned.replace(/^https?:\/\//i, '');
  cleaned = cleaned.replace(/^www\./i, '');
  cleaned = cleaned.split('/')[0].split('?')[0].split('#')[0];

  const parts = cleaned.split('.');
  const name = parts[0];
  const explicitTld = parts.length > 1 ? `.${parts.slice(1).join('.')}` : '.com';
  return { name, explicitTld };
}

// Check backend health
export async function checkBackendHealth(): Promise<BackendStatus> {
  const endpoints = getApiEndpoints('/api/health');

  for (const url of endpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1500);
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        return { connected: true, service: data.service, message: 'FastAPI Backend Online (Free Testing Mode)' };
      }
    } catch {
      // Continue to next endpoint
    }
  }

  return { connected: false, message: 'FastAPI backend offline' };
}

// Fetch extensions from backend if available
export async function getExtensionsList(): Promise<string[]> {
  const endpoints = getApiEndpoints('/api/domains/extensions');

  for (const url of endpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1500);
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.extensions) && data.extensions.length > 0) {
          return data.extensions;
        }
      }
    } catch {
      // Continue to next endpoint
    }
  }

  return POPULAR_EXTENSIONS.map((e) => e.tld);
}

function mapApiItemToUiResult(
  item: ApiDomainResult,
  isFeatured: boolean,
  disclaimer: string
): DomainSearchResult {
  const parts = item.domain.split('.');
  const tld = item.extension || (parts.length > 1 ? `.${parts.slice(1).join('.')}` : '.com');
  const name = item.name || parts[0];

  return {
    domain: item.domain,
    name: name,
    tld: tld,
    status: item.availability,
    statusLabel: item.status_label || (item.availability === 'taken' ? 'Unavailable / Reserved' : 'Unverified – Free for Testing'),
    registry: item.registry || 'Accredited Registry Authority',
    price: {
      registration: 0.00,
      renewal: 0.00,
      currency: item.price?.currency || 'USD',
      discountPercent: undefined,
      periodYears: item.price?.period_years || 1,
      isMock: true,
      pricingNote: 'FREE TESTING MODE: No payment is collected by MasterTools Domains. This does not waive actual registry or accredited registrar fees.',
    },
    isPopular: true,
    isFeatured: isFeatured,
    whoisPrivacyIncluded: true,
    sslIncluded: true,
    vercelReady: true,
    renderReady: true,
    isMock: true,
    disclaimer: disclaimer,
    suggestedAction: item.availability === 'taken' ? 'backorder' : 'verify',
  };
}

// Local mock fallback if backend is unreachable (strictly disabled in production)
function localMockSearch(rawQuery: string): DomainSearchResult[] {
  const { name, explicitTld } = parseDomainQuery(rawQuery);
  if (!name) return [];

  if (name.startsWith('-') || name.endsWith('-')) {
    throw new DomainValidationError('Domain name cannot start or end with a hyphen.', rawQuery);
  }
  if (/[^a-z0-9-]/.test(name)) {
    throw new DomainValidationError('Domain contains invalid characters. Only alphanumeric and hyphens are allowed.', rawQuery);
  }
  if (name.length > 63) {
    throw new DomainValidationError('Domain label exceeds maximum allowed length of 63 characters.', rawQuery);
  }

  const primaryTld = explicitTld || '.com';
  const variations = [
    `${name}${primaryTld}`,
    `${name}.gy`,
    `${name}.com`,
    `${name}.in`,
    `${name}.org`,
    `${name}.net`,
    `get${name}${primaryTld}`,
    `${name}app${primaryTld}`,
  ];

  const reservedNames = ['mastertools', 'google', 'apple', 'gov', 'edu', 'registry', 'admin', 'root'];

  return variations.map((domain, index) => {
    const parts = domain.split('.');
    const itemSld = parts[0];
    const itemTld = '.' + parts.slice(1).join('.');
    const isReserved = reservedNames.includes(itemSld);
    const status: DomainAvailability = isReserved ? 'taken' : 'unverified';

    return {
      domain,
      name: itemSld,
      tld: itemTld,
      status,
      statusLabel: isReserved ? 'Unavailable / Reserved' : 'Unverified – Free for Testing',
      registry: 'Accredited Registry Authority',
      price: {
        registration: 0.00,
        renewal: 0.00,
        currency: 'USD',
        discountPercent: undefined,
        periodYears: 1,
        isMock: true,
        pricingNote: 'FREE TESTING MODE: Free for application testing.',
      },
      isPopular: true,
      isFeatured: index === 0,
      whoisPrivacyIncluded: true,
      sslIncluded: true,
      vercelReady: true,
      renderReady: true,
      isMock: true,
      disclaimer: 'FREE TESTING MODE: No payment is collected by MasterTools Domains.',
      suggestedAction: isReserved ? 'backorder' : 'verify',
    };
  });
}

// Mock fallback disabled by default in production
const ENABLE_MOCK_FALLBACK = !isProd && import.meta.env.VITE_ENABLE_MOCK_FALLBACK === 'true';

export class ServiceUnavailableError extends Error {
  constructor(
    message: string = 'The domain search backend service is currently unreachable. Live registrar verification cannot be performed. Please verify backend connectivity.'
  ) {
    super(message);
    this.name = 'ServiceUnavailableError';
  }
}

export class RegistrationApiError extends Error {
  public status: number;
  public details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'RegistrationApiError';
    this.status = status;
    this.details = details;
  }
}

import type {
  CreateRegistrationRequestPayload,
  UpdateRegistrationRequestPayload,
  RegistrationRequestItem,
  PublicRegistrationRequestItem,
  RegistrationRequestListResponse,
  RegistrationRequestStatus,
  AdminLoginResponse,
} from '../types/domain';

// --- Admin Session Storage Helpers ---
export function getAdminToken(): string | null {
  try {
    return sessionStorage.getItem('mt_admin_session');
  } catch {
    return null;
  }
}

export function setAdminToken(token: string): void {
  try {
    sessionStorage.setItem('mt_admin_session', token);
  } catch {
    // ignore
  }
}

export function clearAdminToken(): void {
  try {
    sessionStorage.removeItem('mt_admin_session');
  } catch {
    // ignore
  }
}

export async function adminLogin(
  username: string,
  password: string
): Promise<AdminLoginResponse> {
  const endpoints = getApiEndpoints('/api/admin/login');
  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const errorMsg =
          data?.detail?.message || 'Invalid administrator username or password.';
        throw new RegistrationApiError(errorMsg, res.status, data?.detail);
      }

      setAdminToken(data.session_token);
      return data as AdminLoginResponse;
    } catch (err) {
      if (err instanceof RegistrationApiError) {
        throw err;
      }
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || 'Could not connect to authentication server.',
    500
  );
}

export async function adminLogout(): Promise<void> {
  const token = getAdminToken();
  clearAdminToken();
  if (!token) return;

  const endpoints = getApiEndpoints('/api/admin/logout');

  for (const url of endpoints) {
    try {
      await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          'X-Admin-Session': token,
        },
      });
      break;
    } catch {
      // ignore logout network errors
    }
  }
}

export async function checkAdminSession(): Promise<{ authenticated: boolean; username: string }> {
  const token = getAdminToken();
  if (!token) {
    return { authenticated: false, username: '' };
  }

  const endpoints = getApiEndpoints('/api/admin/me');

  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-Admin-Session': token,
        },
      });

      if (res.ok) {
        const data = await res.json().catch(() => null);
        if (data?.authenticated) {
          return { authenticated: true, username: data.username };
        }
      }
    } catch {
      // continue to next endpoint
    }
  }

  clearAdminToken();
  return { authenticated: false, username: '' };
}

export async function searchDomains(rawQuery: string): Promise<DomainSearchResult[]> {
  const trimmed = rawQuery.trim();
  if (!trimmed) return [];

  const endpoints = getApiEndpoints(`/api/domains/search?name=${encodeURIComponent(trimmed)}`);

  for (const url of endpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);

      // Handle Validation Error from FastAPI (400)
      if (res.status === 400) {
        const errorData = await res.json().catch(() => null);
        let errorMsg = 'Invalid domain name.';
        if (errorData?.detail?.message) {
          errorMsg = errorData.detail.message;
        } else if (typeof errorData?.detail === 'string') {
          errorMsg = errorData.detail;
        }
        throw new DomainValidationError(errorMsg, trimmed);
      }

      if (res.ok) {
        const data: ApiDomainSearchResponse = await res.json();
        const results: DomainSearchResult[] = [];

        if (data.exact_match) {
          results.push(mapApiItemToUiResult(data.exact_match, true, data.disclaimer));
        }

        if (Array.isArray(data.suggestions)) {
          data.suggestions.forEach((item) => {
            results.push(mapApiItemToUiResult(item, false, data.disclaimer));
          });
        }

        return results;
      }
    } catch (err) {
      if (err instanceof DomainValidationError) {
        throw err;
      }
      // If network failure or abort, try next endpoint
    }
  }

  if (ENABLE_MOCK_FALLBACK) {
    return localMockSearch(trimmed);
  }

  throw new ServiceUnavailableError(
    'The domain search backend service is currently unreachable. Live registrar verification cannot be performed. Please verify backend connectivity.'
  );
}

export async function submitRegistrationRequest(
  payload: CreateRegistrationRequestPayload
): Promise<RegistrationRequestItem> {
  const endpoints = getApiEndpoints('/api/registrations/requests');
  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const errorMsg =
          data?.detail?.message ||
          (typeof data?.detail === 'string' ? data.detail : null) ||
          'Failed to submit registration request.';
        throw new RegistrationApiError(errorMsg, res.status, data?.detail);
      }

      return data as RegistrationRequestItem;
    } catch (err) {
      if (err instanceof RegistrationApiError) {
        throw err;
      }
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || 'Could not connect to the backend server.',
    500
  );
}

export async function getRegistrationRequest(
  requestId: string,
  trackingToken?: string
): Promise<RegistrationRequestItem> {
  const endpoints = getApiEndpoints(`/api/registrations/requests/${encodeURIComponent(requestId)}`);

  const headers: Record<string, string> = {};
  if (trackingToken && trackingToken.trim()) {
    headers['X-Customer-Tracking-Token'] = trackingToken.trim();
  }

  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url, { headers });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const errorMsg =
          data?.detail?.message || `Request '${requestId}' not found.`;
        throw new RegistrationApiError(errorMsg, res.status, data?.detail);
      }

      return data as RegistrationRequestItem;
    } catch (err) {
      if (err instanceof RegistrationApiError) {
        throw err;
      }
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || 'Could not fetch registration request.',
    500
  );
}

export async function getPublicRegistrationRequest(
  requestId: string,
  trackingToken?: string
): Promise<PublicRegistrationRequestItem | RegistrationRequestItem> {
  const endpoints = getApiEndpoints(`/api/registrations/requests/${encodeURIComponent(requestId)}`);

  const headers: Record<string, string> = {};
  if (trackingToken && trackingToken.trim()) {
    headers['X-Customer-Tracking-Token'] = trackingToken.trim();
  }

  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url, { headers });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const errorMsg =
          data?.detail?.message || `Request '${requestId}' not found.`;
        throw new RegistrationApiError(errorMsg, res.status, data?.detail);
      }

      return data;
    } catch (err) {
      if (err instanceof RegistrationApiError) {
        throw err;
      }
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || 'Could not fetch registration request.',
    500
  );
}

export async function listRegistrationRequests(
  statusFilter?: RegistrationRequestStatus
): Promise<RegistrationRequestListResponse> {
  const token = getAdminToken();
  const queryParam = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
  const endpoints = getApiEndpoints(`/api/registrations/requests${queryParam}`);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-Admin-Session'] = token;
  }

  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        headers,
        credentials: 'include',
      });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        if (res.status === 401) {
          throw new RegistrationApiError(
            'Administrator authentication required. Please sign in.',
            401,
            data?.detail
          );
        }
        if (res.status === 403) {
          throw new RegistrationApiError(
            'Access denied. Administrator privileges required.',
            403,
            data?.detail
          );
        }
        const errorMsg = data?.detail?.message || 'Could not list registration requests.';
        throw new RegistrationApiError(errorMsg, res.status, data?.detail);
      }

      return data as RegistrationRequestListResponse;
    } catch (err) {
      if (err instanceof RegistrationApiError) {
        throw err;
      }
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || 'Could not list registration requests.',
    500
  );
}

export async function updateRegistrationRequest(
  requestId: string,
  payload: UpdateRegistrationRequestPayload
): Promise<RegistrationRequestItem> {
  const token = getAdminToken();
  const endpoints = getApiEndpoints(`/api/registrations/requests/${encodeURIComponent(requestId)}`);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    headers['X-Admin-Session'] = token;
  }

  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        method: 'PATCH',
        headers,
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        if (res.status === 401) {
          throw new RegistrationApiError(
            'Administrator authentication required. Please sign in.',
            401,
            data?.detail
          );
        }
        if (res.status === 403) {
          throw new RegistrationApiError(
            'Access denied. Administrator privileges required.',
            403,
            data?.detail
          );
        }
        const errorMsg =
          data?.detail?.message ||
          (typeof data?.detail === 'string' ? data.detail : null) ||
          'Failed to update registration request.';
        throw new RegistrationApiError(errorMsg, res.status, data?.detail);
      }

      return data as RegistrationRequestItem;
    } catch (err) {
      if (err instanceof RegistrationApiError) {
        throw err;
      }
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || 'Could not update registration request.',
    500
  );
}

// ============================================================================
// Real Cloudflare, Vercel & Render Integration Endpoints
// ============================================================================

import type {
  IntegrationConfigStatus,
  ProposedDnsPlan,
  DnsApplyRequest,
  IntegrationDeploymentStatus,
  CloudflareZoneInfo,
} from '../types/domain';

export async function getIntegrationStatus(): Promise<IntegrationConfigStatus> {
  const endpoints = getApiEndpoints('/api/integrations/status');
  for (const url of endpoints) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        return (await res.json()) as IntegrationConfigStatus;
      }
    } catch {
      // try next fallback endpoint if non-prod
    }
  }
  return {
    cloudflare: { configured: false, account_id_set: false, default_zone_id_set: false },
    vercel: { configured: false, project_id_set: false },
    render: { configured: false, service_id_set: false },
  };
}

export async function getProposedDnsPlan(
  domain: string,
  target: 'vercel' | 'render'
): Promise<ProposedDnsPlan> {
  const endpoints = getApiEndpoints(
    `/api/integrations/plan?domain=${encodeURIComponent(domain)}&target=${encodeURIComponent(target)}`
  );

  let lastError: Error | null = null;
  for (const url of endpoints) {
    try {
      const res = await fetch(url);
      const data = await res.json().catch(() => null);
      if (res.ok && data) {
        return data as ProposedDnsPlan;
      }
      if (data?.detail?.message) {
        throw new RegistrationApiError(data.detail.message, res.status);
      }
    } catch (err) {
      if (err instanceof RegistrationApiError) throw err;
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || `Failed to fetch DNS plan for '${domain}'.`,
    500
  );
}

export async function applyDnsPlan(
  request: DnsApplyRequest
): Promise<IntegrationDeploymentStatus> {
  const endpoints = getApiEndpoints('/api/integrations/apply');

  let lastError: Error | null = null;
  for (const url of endpoints) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data) {
        return data as IntegrationDeploymentStatus;
      }
      const errMsg =
        data?.detail?.message ||
        data?.message ||
        `Failed to apply DNS records for '${request.domain}'.`;
      throw new RegistrationApiError(errMsg, res.status);
    } catch (err) {
      if (err instanceof RegistrationApiError) throw err;
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || 'Could not connect to backend to apply DNS changes.',
    500
  );
}

export async function verifyDeployment(
  domain: string,
  target: 'vercel' | 'render'
): Promise<IntegrationDeploymentStatus> {
  const endpoints = getApiEndpoints(
    `/api/integrations/verify?domain=${encodeURIComponent(domain)}&target=${encodeURIComponent(target)}`
  );

  let lastError: Error | null = null;
  for (const url of endpoints) {
    try {
      const res = await fetch(url);
      const data = await res.json().catch(() => null);
      if (res.ok && data) {
        return data as IntegrationDeploymentStatus;
      }
    } catch (err) {
      lastError = err as Error;
    }
  }

  throw new RegistrationApiError(
    lastError?.message || `Failed to verify deployment for '${domain}'.`,
    500
  );
}

export async function getCloudflareZoneInfo(
  domain: string
): Promise<CloudflareZoneInfo | null> {
  const endpoints = getApiEndpoints(
    `/api/integrations/cloudflare/zone?domain=${encodeURIComponent(domain)}`
  );

  for (const url of endpoints) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        return (await res.json()) as CloudflareZoneInfo;
      }
    } catch {
      // ignore
    }
  }
  return null;
}
