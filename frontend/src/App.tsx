import { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { PopularExtensions } from './components/PopularExtensions';
import { DomainSearchResults } from './components/DomainSearchResults';
import { FeaturedDeals } from './components/FeaturedDeals';
import { HowItWorks } from './components/HowItWorks';
import { DeployIntegrations } from './components/DeployIntegrations';
import { FeaturesBenefits } from './components/FeaturesBenefits';
import { CartDrawer } from './components/CartDrawer';
import { QuickConnectModal } from './components/QuickConnectModal';
import { RegistrationRequestModal } from './components/RegistrationRequestModal';
import { AdminDashboardModal } from './components/AdminDashboardModal';
import { Footer } from './components/Footer';

import type {
  DomainSearchResult,
  CartItem,
  FeaturedDeal,
} from './types/domain';
import {
  checkBackendHealth,
  getExtensionsList,
  searchDomains,
  DomainValidationError,
  ServiceUnavailableError,
} from './api/domainService';
import type { BackendStatus } from './api/domainService';
import { Check, X } from 'lucide-react';

export function App() {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<DomainSearchResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [availableExtensions, setAvailableExtensions] = useState<string[]>(['.gy']);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({
    connected: false,
    message: 'Checking FastAPI status...',
  });
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [isCartOpen, setIsCartOpen] = useState<boolean>(false);
  const [quickConnectDomain, setQuickConnectDomain] = useState<DomainSearchResult | null>(null);
  const [requestModalDomain, setRequestModalDomain] = useState<DomainSearchResult | null>(null);
  const [isAdminOpen, setIsAdminOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  };

  const executeSearch = useCallback(async (query: string, preferredTld?: string) => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setIsSearching(true);
    setSearchError(null);
    setSearchQuery(trimmed);

    try {
      const results = await searchDomains(trimmed);
      let finalResults = results;

      if (preferredTld) {
        // Move preferred TLD to top
        finalResults = [
          ...results.filter((r) => r.tld === preferredTld),
          ...results.filter((r) => r.tld !== preferredTld),
        ];
      }

      setSearchResults(finalResults);
    } catch (err: unknown) {
      if (err instanceof DomainValidationError) {
        setSearchError(err.message);
        setSearchResults([]);
      } else if (err instanceof ServiceUnavailableError) {
        setSearchError(err.message);
        setSearchResults([]);
      } else if (err instanceof Error) {
        setSearchError(err.message || 'Error communicating with search engine.');
        setSearchResults([]);
      } else {
        setSearchError('An unexpected error occurred.');
        setSearchResults([]);
      }
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Initialize: Check backend and load extensions
  useEffect(() => {
    async function init() {
      const status = await checkBackendHealth();
      setBackendStatus(status);

      const exts = await getExtensionsList();
      if (exts && exts.length > 0) {
        setAvailableExtensions(exts);
      }

      // Initial search query demo (tala)
      executeSearch('tala');
    }
    init();
  }, [executeSearch]);

  // Handle extension or showcase pill click from PopularExtensions
  const handleSelectExtension = (queryOrSlug: string) => {
    const slug = queryOrSlug.replace(/\.gy$/i, '').trim();
    executeSearch(slug, '.gy');

    const el = document.getElementById('search-results-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Add domain to Cart
  const handleAddToCart = (item: DomainSearchResult) => {
    if (cartItems.some((ci) => ci.domain === item.domain)) {
      showToast(`${item.domain} is already in your registration queue!`);
      return;
    }

    const newItem: CartItem = {
      domain: item.domain,
      tld: item.tld,
      status: item.status,
      price: item.price,
      years: 1,
      connectTarget: 'vercel',
      whoisPrivacy: true,
    };

    setCartItems((prev) => [...prev, newItem]);
    showToast(`Added ${item.domain} to your .gy registration queue`);
  };

  // Handle Claim Deal / Showcase
  const handleClaimDeal = (deal: FeaturedDeal) => {
    const target = deal.sampleDomain
      ? deal.sampleDomain.replace(/\.gy$/i, '')
      : 'tala';
    executeSearch(target, '.gy');

    const el = document.getElementById('search-results-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    showToast(`Searching .gy showcase for ${deal.sampleDomain || 'tala.gy'}`);
  };

  const handleRemoveCartItem = (domain: string) => {
    setCartItems((prev) => prev.filter((i) => i.domain !== domain));
  };

  const handleUpdateYears = (domain: string, years: number) => {
    setCartItems((prev) =>
      prev.map((i) => (i.domain === domain ? { ...i, years } : i))
    );
  };

  const handleUpdateTarget = (
    domain: string,
    target: 'vercel' | 'render' | 'none'
  ) => {
    setCartItems((prev) =>
      prev.map((i) => (i.domain === domain ? { ...i, connectTarget: target } : i))
    );
  };

  const handleClearCart = () => {
    setCartItems([]);
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-2xl border border-indigo-500/40 bg-[#0e1629]/95 px-4 py-3 shadow-2xl backdrop-blur-md">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
            <Check className="h-4 w-4" />
          </div>
          <span className="text-xs sm:text-sm font-medium text-slate-100">
            {toastMessage}
          </span>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-slate-400 hover:text-white cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 1. Navigation */}
      <Navbar
        backendStatus={backendStatus}
        cartCount={cartItems.length}
        onOpenCart={() => setIsCartOpen(true)}
        onOpenAdmin={() => setIsAdminOpen(true)}
        onSelectNav={(id) => {
          const el = document.getElementById(id);
          if (el) el.scrollIntoView({ behavior: 'smooth' });
        }}
      />

      <main className="flex-1">
        {/* 2 & 3. Hero Section & Domain Search Bar */}
        <HeroSection
          onSearch={(q, tld) => executeSearch(q, tld)}
          isLoading={isSearching}
          initialQuery={searchQuery}
          availableExtensions={availableExtensions}
        />

        {/* 4. Popular Extensions: .com, .in, .xyz, .dev, .net, .org, .app */}
        <PopularExtensions
          onSelectExtension={handleSelectExtension}
          selectedTld={searchQuery.includes('.') ? `.${searchQuery.split('.').pop()}` : undefined}
        />

        {/* 5. Domain Search Results with availability badges, pricing, and filters */}
        <DomainSearchResults
          results={searchResults}
          isLoading={isSearching}
          searchQuery={searchQuery}
          errorMessage={searchError}
          cartItems={cartItems}
          onAddToCart={handleAddToCart}
          onOpenQuickConnect={(item) => setQuickConnectDomain(item)}
          onRequestRegistration={(item) => setRequestModalDomain(item)}
          onTrySuggestion={(name) => executeSearch(name)}
        />

        {/* 6. Featured Domain Deals */}
        <FeaturedDeals onClaimDeal={handleClaimDeal} />

        {/* 7. How it works: Search → Register → Connect → Launch */}
        <HowItWorks />

        {/* 8. Vercel and Render Integration Section */}
        <DeployIntegrations />

        {/* 9. Features and Benefits */}
        <FeaturesBenefits />
      </main>

      {/* 10. Footer */}
      <Footer />

      {/* Cart Drawer */}
      <CartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        items={cartItems}
        onRemoveItem={handleRemoveCartItem}
        onUpdateYears={handleUpdateYears}
        onUpdateTarget={handleUpdateTarget}
        onClearCart={handleClearCart}
      />

      {/* 1-Click DNS Quick Connect Modal */}
      <QuickConnectModal
        domainItem={quickConnectDomain}
        onClose={() => setQuickConnectDomain(null)}
      />

      {/* Manual .GY Registration Request Modal */}
      <RegistrationRequestModal
        isOpen={!!requestModalDomain}
        domainItem={requestModalDomain}
        onClose={() => setRequestModalDomain(null)}
        onSuccess={(req) => {
          showToast(`Request ${req.request_id} created for ${req.domain}`);
        }}
      />

      {/* Admin Dashboard & Registrar Coordination Modal */}
      <AdminDashboardModal
        isOpen={isAdminOpen}
        onClose={() => setIsAdminOpen(false)}
      />
    </div>
  );
}

export default App;
