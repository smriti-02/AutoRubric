'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export function Navigation() {
  const { token, doLogout } = useAuth();
  const pathname = usePathname();

  if (pathname === '/login') return null;

  return (
    <header className="sticky top-0 z-50 glass-nav transition-all duration-300">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link 
            href="/" 
            className="flex items-center gap-2 font-semibold text-[15px] tracking-tight text-zinc-900 hover:opacity-80 transition-opacity"
          >
            <div className="w-5 h-5 rounded-md bg-zinc-900 flex items-center justify-center text-white text-[10px] font-bold">
              A
            </div>
            AutoRubric
          </Link>

          {token && (
            <nav className="flex items-center gap-1 sm:gap-2">
              <Link 
                href="/" 
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  pathname === '/' 
                    ? 'text-zinc-900 bg-black/[0.04]' 
                    : 'text-zinc-500 hover:text-zinc-900 hover:bg-black/[0.02]'
                }`}
              >
                Dashboard
              </Link>
              <Link 
                href="/upload" 
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  pathname === '/upload' 
                    ? 'text-zinc-900 bg-black/[0.04]' 
                    : 'text-zinc-500 hover:text-zinc-900 hover:bg-black/[0.02]'
                }`}
              >
                Upload
              </Link>
            </nav>
          )}
        </div>

        {token && (
          <div className="flex items-center gap-3">
            <button 
              onClick={doLogout} 
              className="text-xs font-medium text-zinc-500 hover:text-zinc-900 px-3 py-1.5 rounded-full hover:bg-black/[0.04] transition-colors"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
