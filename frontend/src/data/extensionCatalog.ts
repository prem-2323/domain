import type { TldExtensionInfo, FeaturedDeal } from '../types/domain';

export const GY_REGISTRY_INFO = {
  extension: '.gy',
  registryName: 'University of Guyana .GY Registry',
  directoryUrl: 'https://registry.gy/registrars/',
  standardAnnualPrice: 45.00,
  description: 'The official country-code top-level domain (ccTLD) for Guyana, operated through accredited registrars.',
};

export const POPULAR_EXTENSIONS: TldExtensionInfo[] = [
  {
    tld: '.gy',
    category: 'ccTLD',
    startingPrice: 45.00,
    regularPrice: 45.00,
    tagline: 'Official country-code domain for Guyana (Managed by University of Guyana)',
    popular: true,
    badge: 'Exclusive ccTLD',
    registry: 'University of Guyana .GY Registry',
    officialUrl: 'https://registry.gy/registrars/',
  },
];

export const FEATURED_DEALS: FeaturedDeal[] = [
  {
    id: 'usecase-tala',
    tld: '.gy',
    headline: 'Modern Digital Identities',
    description: 'Clean personal branding, personal websites, and founder links hosted on Vercel or Render.',
    salePrice: 45.00,
    originalPrice: 45.00,
    badge: 'Personal & Creator',
    badgeColor: 'blue',
    featuredFor: 'Creators, Founders & Portfolios',
    sampleDomain: 'tala.gy',
  },
  {
    id: 'usecase-prem',
    tld: '.gy',
    headline: 'High-Impact Short Names',
    description: 'Ultra-memorable short names with Cloudflare Anycast DNS and sub-60s edge propagation.',
    salePrice: 45.00,
    originalPrice: 45.00,
    badge: 'Short & Punchy',
    badgeColor: 'purple',
    featuredFor: 'Tech Startups & APIs',
    sampleDomain: 'prem.gy',
  },
  {
    id: 'usecase-mastertools',
    tld: '.gy',
    headline: 'Enterprise Cloud & SaaS',
    description: 'Deploy full-stack web applications and microservices with automated Let\'s Encrypt SSL.',
    salePrice: 45.00,
    originalPrice: 45.00,
    badge: 'SaaS Platform',
    badgeColor: 'emerald',
    featuredFor: 'Cloud & Developer Stacks',
    sampleDomain: 'mastertools.gy',
  },
  {
    id: 'usecase-myshop',
    tld: '.gy',
    headline: 'Guyana & Global Commerce',
    description: 'Regional e-commerce storefronts and business presences with verified .gy trust.',
    salePrice: 45.00,
    originalPrice: 45.00,
    badge: 'Business & Store',
    badgeColor: 'amber',
    featuredFor: 'Local & Regional Brands',
    sampleDomain: 'myshop.gy',
  },
];
