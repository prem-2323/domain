export type DomainAvailability = 'available' | 'taken' | 'premium' | 'unverified';

export interface DomainPrice {
  registration: number; // in USD
  renewal: number; // in USD
  currency: string;
  discountPercent?: number;
  periodYears: number;
  isMock?: boolean;
  pricingNote?: string;
}

export interface DomainSearchResult {
  domain: string;
  name: string;
  tld: string;
  status: DomainAvailability;
  statusLabel?: string;
  registry?: string;
  price: DomainPrice;
  isPopular?: boolean;
  isFeatured?: boolean;
  whoisPrivacyIncluded: boolean;
  sslIncluded: boolean;
  vercelReady: boolean;
  renderReady: boolean;
  isMock: boolean;
  disclaimer?: string;
  suggestedAction?: 'buy' | 'make_offer' | 'backorder' | 'verify';
}

export interface ApiDomainPrice {
  registration_price: number;
  renewal_price: number;
  currency: string;
  discount_percent?: number;
  period_years: number;
  is_mock: boolean;
  pricing_note?: string;
}

export interface ApiDomainResult {
  domain: string;
  name: string;
  extension: string;
  availability: DomainAvailability;
  price: ApiDomainPrice;
  is_exact_match: boolean;
  status_label?: string;
  registry?: string;
  features: string[];
  is_mock: boolean;
}

export interface ApiDomainSearchResponse {
  query: string;
  normalized_name: string;
  extension: string;
  registry: string;
  official_registrars_url: string;
  is_valid: boolean;
  exact_match: ApiDomainResult | null;
  suggestions: ApiDomainResult[];
  total_results: number;
  is_mock: boolean;
  disclaimer: string;
}

export interface TldExtensionInfo {
  tld: string;
  category: string;
  startingPrice: number;
  regularPrice: number;
  tagline: string;
  popular?: boolean;
  badge?: string;
  registry?: string;
  officialUrl?: string;
}

export interface FeaturedDeal {
  id: string;
  tld: string;
  headline: string;
  description: string;
  salePrice: number;
  originalPrice: number;
  discount?: string;
  badge: string;
  badgeColor: string;
  featuredFor: string;
  sampleDomain: string;
}

export interface CartItem {
  domain: string;
  tld: string;
  status: DomainAvailability;
  price: DomainPrice;
  years: number;
  connectTarget?: 'vercel' | 'render' | 'none';
  whoisPrivacy: boolean;
}

export type RegistrationRequestStatus =
  | 'pending'
  | 'verification_required'
  | 'verified_available'
  | 'unavailable'
  | 'registration_in_progress'
  | 'registered'
  | 'rejected';

export interface CreateRegistrationRequestPayload {
  customer_name: string;
  customer_email: string;
  domain: string;
  message?: string;
}

export interface UpdateRegistrationRequestPayload {
  status?: RegistrationRequestStatus;
  admin_notes?: string;
  confirmed_price?: number;
  confirmation_reference?: string;
}

export interface RegistrationRequestItem {
  request_id: string;
  tracking_token?: string;
  domain: string;
  customer_name?: string;
  customer_email?: string;
  message?: string | null;
  status: RegistrationRequestStatus;
  status_label: string;
  estimated_annual_price: number;
  confirmed_price?: number | null;
  pricing_type?: 'estimated' | 'confirmed' | 'free_testing';
  pricing_amount?: number;
  currency: string;
  admin_notes?: string | null;
  confirmation_reference?: string | null;
  created_at: string;
  updated_at: string;
  disclaimer: string;
}

export interface PublicRegistrationRequestItem {
  request_id: string;
  domain: string;
  status: RegistrationRequestStatus;
  status_label: string;
  pricing_type: 'estimated' | 'confirmed' | 'free_testing';
  pricing_amount: number;
  currency: string;
  created_at: string;
  updated_at: string;
  disclaimer: string;
}

export interface AdminLoginResponse {
  session_token: string;
  username: string;
  expires_at: string;
  message: string;
}

export interface RegistrationRequestListResponse {
  total: number;
  requests: RegistrationRequestItem[];
}
