import React from 'react';
import { DomainSearchBar } from './DomainSearchBar';
import { Shield, Zap, Server, CheckCircle2 } from 'lucide-react';

interface HeroSectionProps {
  onSearch: (query: string, preferredTld?: string) => void;
  isLoading: boolean;
  initialQuery?: string;
  availableExtensions: string[];
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onSearch,
  isLoading,
  initialQuery,
  availableExtensions,
}) => {
  return (
    <section id="search-section" className="relative w-full pt-16 pb-12 sm:pt-24 sm:pb-16 overflow-hidden">
      {/* Background ambient light effects */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[450px] bg-gradient-to-b from-emerald-600/15 via-teal-600/10 to-transparent blur-[140px] pointer-events-none rounded-full" />
      <div className="absolute top-24 left-1/4 w-[350px] h-[350px] bg-indigo-600/10 blur-[130px] pointer-events-none rounded-full" />

      {/* Subtle grid pattern background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293710_1px,transparent_1px),linear-gradient(to_bottom,#1f293710_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

      <div className="relative z-10 mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
        {/* Eyebrow Pill */}
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold text-emerald-300 shadow-sm backdrop-blur-md mb-6 hover:border-emerald-500/50 transition-colors">
          <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>FREE TESTING MODE</span>
          <span className="text-slate-500">•</span>
          <span className="text-teal-300">All Extensions Supported (.gy, .com, .in, .org, .net, .io, .ai)</span>
        </div>

        {/* Main Headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white mb-6 leading-[1.1]">
          Find your perfect{' '}
          <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
            domain for free.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="mx-auto max-w-2xl text-base sm:text-lg text-slate-400 mb-10 leading-relaxed font-normal">
          Search across <strong>all domain extensions</strong> in Free Application Testing Mode. Submit registration requests, track progress securely, and prepare Cloudflare Anycast DNS for Vercel and Render.
        </p>

        {/* Search Bar Component */}
        <div className="mb-10">
          <DomainSearchBar
            onSearch={onSearch}
            isLoading={isLoading}
            initialQuery={initialQuery}
            availableExtensions={availableExtensions}
          />
        </div>

        {/* Value Props Row */}
        <div className="flex flex-wrap items-center justify-center gap-y-3 gap-x-8 text-xs sm:text-sm text-slate-400">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-300 font-medium">Free Testing Mode ($0.00)</span>
          </div>

          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-teal-400" />
            <span className="text-slate-300 font-medium">1-Click Vercel & Render Setup</span>
          </div>

          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-indigo-400" />
            <span className="text-slate-300 font-medium">Cloudflare Anycast DNS</span>
          </div>

          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-blue-400" />
            <span className="text-slate-300 font-medium">Multi-TLD Catalog (.gy, .com, .in...)</span>
          </div>
        </div>
      </div>
    </section>
  );
};
