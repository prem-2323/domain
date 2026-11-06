import React, { useState } from 'react';
import { Search, X, Loader2, Sparkles } from 'lucide-react';

interface DomainSearchBarProps {
  onSearch: (query: string, preferredTld?: string) => void;
  isLoading: boolean;
  initialQuery?: string;
  availableExtensions?: string[];
}

export const DomainSearchBar: React.FC<DomainSearchBarProps> = ({
  onSearch,
  isLoading,
  initialQuery = '',
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [prevInitialQuery, setPrevInitialQuery] = useState(initialQuery);

  if (initialQuery !== prevInitialQuery) {
    setPrevInitialQuery(initialQuery);
    setQuery(initialQuery);
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    onSearch(trimmed, '.gy');
  };

  const handleClear = () => {
    setQuery('');
  };

  const sampleSuggestions = ['tala', 'prem', 'mastertools', 'myshop', 'myportfolio'];

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    onSearch(suggestion, '.gy');
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Search Input Box */}
      <form
        onSubmit={handleSubmit}
        className="relative group rounded-2xl bg-gradient-to-r from-blue-500/20 via-indigo-500/30 to-purple-500/20 p-[1.5px] shadow-2xl shadow-indigo-950/50 transition-all duration-300 hover:shadow-indigo-500/20 focus-within:shadow-indigo-500/30"
      >
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center rounded-[15px] bg-[#0c1222] p-2 sm:p-2.5 gap-2 backdrop-blur-xl border border-slate-800/80">
          {/* Search Icon & Text Input */}
          <div className="relative flex flex-1 items-center pl-3">
            <Search className="h-5 w-5 text-indigo-400 shrink-0 transition-colors group-focus-within:text-blue-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your name (e.g. tala, prem, mastertools, myshop)..."
              className="w-full bg-transparent px-3 py-3 text-base sm:text-lg text-white placeholder-slate-400 focus:outline-none"
              autoComplete="off"
              spellCheck="false"
            />
            {query && !isLoading && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                aria-label="Clear search input"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Fixed .gy Extension Badge */}
          <div className="flex items-center border-t sm:border-t-0 sm:border-l border-slate-800/80 pt-2 sm:pt-0 sm:pl-2">
            <div
              title="MasterTools Domains focuses exclusively on the .gy ccTLD"
              className="flex items-center justify-center gap-1.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 px-3.5 py-2.5 text-xs font-semibold text-indigo-200 select-none w-full sm:w-auto"
            >
              <span className="font-mono text-emerald-400 font-bold text-sm">.gy</span>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">ccTLD</span>
            </div>
          </div>

          {/* Search Button */}
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 px-6 py-3 text-sm sm:text-base font-semibold text-white shadow-lg shadow-indigo-600/25 transition-all duration-200 hover:brightness-110 hover:shadow-indigo-600/40 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Checking...</span>
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                <span>Search .gy</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Quick Suggestions */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-400">
        <span className="flex items-center gap-1 text-slate-400">
          <Sparkles className="h-3 w-3 text-indigo-400" />
          Try .gy names:
        </span>
        {sampleSuggestions.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => handleSuggestionClick(item)}
            className="rounded-full border border-slate-800/80 bg-slate-900/60 px-2.5 py-0.5 font-mono text-slate-300 hover:border-indigo-500/50 hover:bg-slate-850 hover:text-indigo-300 transition-all cursor-pointer"
          >
            {item}.gy
          </button>
        ))}
      </div>
    </div>
  );
};
