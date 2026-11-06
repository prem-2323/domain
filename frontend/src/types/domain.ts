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

export type IntegrationWorkflowState =
  | 'not_connected'
  | 'credentials_missing'
  | 'zone_pending_activation'
  | 'awaiting_nameserver_update'
  | 'dns_conflict'
  | 'awaiting_approval'
  | 'provisioning'
  | 'dns_verification_pending'
  | 'connected'
  | 'failed';

export interface DnsRecordItem {
  id?: string;
  type: string;
  name: string;
  content: string;
  ttl: number;
  proxied: boolean;
  purpose?: string;
  comment?: string;
}

export interface CloudflareZoneInfo {
  zone_id: string;
  name: string;
  status: string;
  name_servers: string[];
  original_name_servers?: string[];
  paused: boolean;
  ssl_status?: string;
  account_id?: string;
  account_name?: string;
}

export interface DnsConflict {
  existing_record: DnsRecordItem;
  proposed_record: DnsRecordItem;
  conflict_type: string;
  message: string;
  requires_override: boolean;
}

export interface ProposedDnsPlan {
  plan_id?: string;
  plan_version?: number;
  created_at?: string;
  expires_at?: string;
  plan_signature?: string;
  existing_records_hash?: string;
  domain: string;
  target_platform: 'vercel' | 'render';
  zone_id?: string;
  zone_name?: string;
  zone_status?: string;
  assigned_nameservers: string[];
  is_zone_active: boolean;
  required_records: DnsRecordItem[];
  existing_records: DnsRecordItem[];
  conflicts: DnsConflict[];
  has_conflicts: boolean;
  state: IntegrationWorkflowState;
  message: string;
  can_apply: boolean;
  requires_approval: boolean;
}

export interface DnsApplyRequest {
  domain: string;
  target_platform: 'vercel' | 'render';
  plan_id: string;
  plan_signature: string;
  expires_at: string;
  approved: boolean;
  override_conflicts?: boolean;
}

export interface DnsVerificationItem {
  type: string;
  name: string;
  expected: string;
  actual: string[];
  verified: boolean;
  error?: string;
}

export interface IntegrationDeploymentStatus {
  domain: string;
  target_platform: 'vercel' | 'render';
  state: IntegrationWorkflowState;
  message: string;
  zone_status?: string;
  assigned_nameservers: string[];
  nameserver_instructions?: string;
  ssl_status?: string;
  ssl_verified: boolean;
  platform_verified: boolean;
  records: DnsRecordItem[];
  verification_items: DnsVerificationItem[];
  conflicts: DnsConflict[];
  last_checked_at: string;
}

export interface IntegrationConfigStatus {
  cloudflare: {
    configured: boolean;
    account_id_set: boolean;
    default_zone_id_set: boolean;
  };
  vercel: {
    configured: boolean;
    project_id_set: boolean;
  };
  render: {
    configured: boolean;
    service_id_set: boolean;
  };
}
