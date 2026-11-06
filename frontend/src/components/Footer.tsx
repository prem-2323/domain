import React from 'react';
import { Globe, Shield, ExternalLink } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-800 bg-[#05070d] text-slate-400 text-xs">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-14">
        {/* Main Columns */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-12">
          {/* Brand info */}
          <div className="col-span-2 space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-600 text-white shadow-md">
                <Globe className="h-5 w-5" />
              </div>
              <span className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                MasterTools
                <span className="rounded-md bg-emerald-500/15 border border-emerald-500/30 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300 uppercase">
                  .GY Domains
                </span>
              </span>
            </div>

            <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
              The premier platform for Guyana's official .gy ccTLD. Search, verify registry availability, coordinate registration through accredited partners, and seamlessly link custom domains to Vercel and Render.
            </p>

            {/* Live Status indicator */}
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-[#0c111e] px-3 py-1.5 text-xs text-slate-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>University of Guyana .GY Registry Sync</span>
              <span className="text-slate-500">•</span>
              <span className="font-mono text-emerald-400 text-[11px]">Accredited Fulfillment</span>
            </div>
          </div>

          {/* Column: .GY Extensions */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
              .GY Showcase
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a href="#search-results-section" className="hover:text-emerald-300 transition-colors">
                  tala.gy (Digital Identity)
                </a>
              </li>
              <li>
                <a href="#search-results-section" className="hover:text-emerald-300 transition-colors">
                  prem.gy (Tech & APIs)
                </a>
              </li>
              <li>
                <a href="#search-results-section" className="hover:text-emerald-300 transition-colors">
                  mastertools.gy (SaaS Platform)
                </a>
              </li>
              <li>
                <a href="#search-results-section" className="hover:text-emerald-300 transition-colors">
                  myshop.gy (Commerce)
                </a>
              </li>
              <li>
                <a href="#search-results-section" className="hover:text-emerald-300 transition-colors">
                  myportfolio.gy (Developers)
                </a>
              </li>
              <li>
                <a
                  href="https://registry.gy/registrars/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:text-emerald-300 transition-colors flex items-center gap-1 font-medium"
                >
                  <span>.GY Registrar Directory</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Column: Cloud Integrations */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
              Cloud Bridge
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a href="#deploy-integrations" className="hover:text-white transition-colors flex items-center gap-1">
                  <span>Connect to Vercel</span>
                </a>
              </li>
              <li>
                <a href="#deploy-integrations" className="hover:text-white transition-colors flex items-center gap-1">
                  <span>Connect to Render</span>
                </a>
              </li>
              <li>
                <a href="#deploy-integrations" className="hover:text-white transition-colors">
                  Cloudflare Anycast DNS
                </a>
              </li>
              <li>
                <a href="#deploy-integrations" className="hover:text-white transition-colors">
                  Automated SSL Certificates
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-white transition-colors">
                  Sub-60s DNS Sync
                </a>
              </li>
            </ul>
          </div>

          {/* Column: Support & Company */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
              Registry & Legal
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <a
                  href="https://registry.gy/registrars/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors flex items-center gap-1"
                >
                  <span>Accredited Registrars</span>
                  <ExternalLink className="h-3 w-3 text-slate-500" />
                </a>
              </li>
              <li>
                <a href="#" onClick={(e) => { e.preventDefault(); alert('University of Guyana .GY ccTLD Registry oversight and policies apply to all .gy domain allocations.'); }} className="hover:text-white transition-colors">
                  .GY Registry Guidelines
                </a>
              </li>
              <li>
                <a href="#" onClick={(e) => { e.preventDefault(); alert('WHOIS Lookup: Query live University of Guyana .gy domain records.'); }} className="hover:text-white transition-colors">
                  .GY WHOIS Directory
                </a>
              </li>
              <li>
                <a href="#" onClick={(e) => { e.preventDefault(); alert('Terms of Service: Standard domain coordination and DNS provisioning terms.'); }} className="hover:text-white transition-colors">
                  Terms of Service
                </a>
              </li>
              <li>
                <a href="#" onClick={(e) => { e.preventDefault(); alert('Privacy Policy: Free lifetime WHOIS privacy commitment for all users.'); }} className="hover:text-white transition-colors">
                  Privacy Policy
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Banner & Disclaimer */}
        <div className="pt-8 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
          <div className="text-slate-400 text-center sm:text-left">
            &copy; {new Date().getFullYear()} MasterTools Domains. Built for modern cloud builders. .GY ccTLD managed by the University of Guyana .GY Registry.
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <Shield className="h-3.5 w-3.5" />
              <span>Free WHOIS Privacy Guaranteed</span>
            </span>
            <span>•</span>
            <a
              href="https://registry.gy/registrars/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-white flex items-center gap-1"
            >
              <span>Official Registrars</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};
