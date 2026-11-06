import type {
  DomainSearchResult,
  DomainAvailability,
  ApiDomainSearchResponse,
  ApiDomainResult,
} from '../types/domain';
import { POPULAR_EXTENSIONS } from '../data/extensionCatalog';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

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

// Clean and extract name, strictly targeting .gy
export function parseDomainQuery(rawQuery: string): { name: string; explicitTld: string } {
  let cleaned = rawQuery.trim().toLowerCase();
  cleaned = cleaned.replace(/^https?:\/\//i, '');
  cleaned = cleaned.replace(/^www\./i, '');
  cleaned = cleaned.split('/')[0].split('?')[0].split('#')[0];

  const parts = cleaned.split('.');
  const name = parts[0];
  return { name, explicitTld: '.gy' };
}

// Check backend health
export async function checkBackendHealth(): Promise<BackendStatus> {
  const endpoints = [
    `${API_BASE_URL}/api/health`,
    'http://localhost:8000/api/health',
  ];

  for (const url of endpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1200);
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        return { connected: true, service: data.service, message: 'FastAPI Backend Online' };
      }
    } catch {
      // Continue to next endpoint
    }
  }

  return { connected: false, message: 'FastAPI backend offline (Running in Standalone Mock Mode)' };
}

// Fetch extensions from backend if available, fallback to [.gy]
export async function getExtensionsList(): Promise<string[]> {
  const endpoints = [
    `${API_BASE_URL}/api/domains/extensions`,
    'http://localhost:8000/api/domains/extensions',
  ];

  for (const url of endpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1200);
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
  return {
    domain: item.domain,
    name: item.name,
    tld: '.gy',
    status: item.availability,
    statusLabel: item.status_label || (item.availability === 'taken' ? 'Unavailable / Reserved' : 'Unverified (.GY Registrar Check Required)'),
    registry: item.registry || 'University of Guyana .GY Registry',
    price: {
      registration: item.price.registration_price,
      renewal: item.price.renewal_price,
      currency: item.price.currency,
      discountPercent: undefined, // No deceptive fake discounts
      periodYears: item.price.period_years,
      isMock: true,
      pricingNote: item.price.pricing_note || 'Official .GY accredited registrar estimated rate.',
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

// Local mock fallback if backend is unreachable
function localMockSearch(rawQuery: string): DomainSearchResult[] {
  const { name } = parseDomainQuery(rawQuery);
  if (!name) return [];

  // Local basic validation check
  if (name.startsWith('-') || name.endsWith('-')) {
    throw new DomainValidationError('Domain name cannot start or end with a hyphen.', rawQuery);
  }
  if (/[^a-z0-9-]/.test(name)) {
    throw new DomainValidationError('Domain contains invalid characters. Only alphanumeric and hyphens are allowed.', rawQuery);
  }
  if (name.length > 63) {
    throw new DomainValidationError('Domain label exceeds maximum allowed length of 63 characters.', rawQuery);
  }

  const variations = [
    `${name}.gy`,
    `get${name}.gy`,
    `${name}app.gy`,
    `my${name}.gy`,
    `${name}hq.gy`,
    `${name}dev.gy`,
    `${name}cloud.gy`,
    `${name}tech.gy`,
  ];

  const reservedNames = ['mastertools', 'google', 'apple', 'gov', 'edu', 'registry', 'guyana'];

  return variations.map((domain, index) => {
    const itemSld = domain.replace('.gy', '');
    const isReserved = reservedNames.includes(itemSld);
    const status: DomainAvailability = isReserved ? 'taken' : 'unverified';

    return {
      domain,
      name: itemSld,
      tld: '.gy',
      status,
      statusLabel: isReserved ? 'Unavailable / Reserved by .GY Registry' : 'Unverified – Real Registrar Check Required',
      registry: 'University of Guyana .GY Registry',
      price: {
        registration: 45.00,
        renewal: 45.00,
        currency: 'USD',
        discountPercent: undefined,
        periodYears: 1,
        isMock: true,
        pricingNote: 'Official .GY accredited registrar estimated rate.',
      },
      isPopular: true,
      isFeatured: index === 0,
      whoisPrivacyIncluded: true,
      sslIncluded: true,
      vercelReady: true,
      renderReady: true,
      isMock: true,
      disclaimer: 'MasterTools Domains operates exclusively with .gy ccTLD domains.',
      suggestedAction: isReserved ? 'backorder' : 'verify',
    };
  });
}

// Check if mock fallback is explicitly enabled by configuration
const ENABLE_MOCK_FALLBACK = import.meta.env.VITE_ENABLE_MOCK_FALLBACK === 'true';

export class ServiceUnavailableError extends Error {
  constructor(
    message: string = 'The .GY domain search backend service is currently offline or unreachable. Live registry verification cannot be performed.'
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
  const endpoints = [
    `${API_BASE_URL}/api/admin/login`,
    'http://localhost:8000/api/admin/login',
  ];

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

  const endpoints = [
    `${API_BASE_URL}/api/admin/logout`,
    'http://localhost:8000/api/admin/logout',
  ];

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

  const endpoints = [
    `${API_BASE_URL}/api/admin/me`,
    'http://localhost:8000/api/admin/me',
  ];

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

  const endpoints = [
    `${API_BASE_URL}/api/domains/search?name=${encodeURIComponent(trimmed)}`,
    `http://localhost:8000/api/domains/search?name=${encodeURIComponent(trimmed)}`,
  ];

  for (const url of endpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);
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

  // Fallback to local mock ONLY if explicitly enabled by configuration
  if (ENABLE_MOCK_FALLBACK) {
    return localMockSearch(trimmed);
  }

  throw new ServiceUnavailableError(
    'The .GY domain search backend service is currently unreachable. Live registrar verification cannot be performed. Please verify backend connectivity.'
  );
}

export async function submitRegistrationRequest(
  payload: CreateRegistrationRequestPayload
): Promise<RegistrationRequestItem> {
  const endpoints = [
    `${API_BASE_URL}/api/registrations/requests`,
    'http://localhost:8000/api/registrations/requests',
  ];

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
  requestId: string
): Promise<RegistrationRequestItem> {
  const endpoints = [
    `${API_BASE_URL}/api/registrations/requests/${encodeURIComponent(requestId)}`,
    `http://localhost:8000/api/registrations/requests/${encodeURIComponent(requestId)}`,
  ];

  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url);
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
  token?: string
): Promise<PublicRegistrationRequestItem | RegistrationRequestItem> {
  const queryParam = token ? `?token=${encodeURIComponent(token)}` : '';
  const endpoints = [
    `${API_BASE_URL}/api/registrations/requests/${encodeURIComponent(requestId)}${queryParam}`,
    `http://localhost:8000/api/registrations/requests/${encodeURIComponent(requestId)}${queryParam}`,
  ];

  let lastError: Error | null = null;

  for (const url of endpoints) {
    try {
      const res = await fetch(url);
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
  const endpoints = [
    `${API_BASE_URL}/api/registrations/requests${queryParam}`,
    `http://localhost:8000/api/registrations/requests${queryParam}`,
  ];

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
  const endpoints = [
    `${API_BASE_URL}/api/registrations/requests/${encodeURIComponent(requestId)}`,
    `http://localhost:8000/api/registrations/requests/${encodeURIComponent(requestId)}`,
  ];

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
