'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { ShieldCheck, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const { doLogin } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      await doLogin({ username, password });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 overflow-hidden">
      {/* Ambient background glow orbs */}
      <div className="ambient-glow -top-32 -left-32 w-96 h-96 bg-blue-100/60" />
      <div className="ambient-glow -bottom-32 -right-32 w-96 h-96 bg-purple-100/50" />
      <div className="ambient-glow top-1/3 right-1/4 w-80 h-80 bg-zinc-200/40" />

      {/* Glassmorphic card */}
      <div className="relative w-full max-w-[420px] glass-card rounded-3xl p-8 sm:p-10 transition-all duration-300">
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-zinc-900 flex items-center justify-center text-white shadow-md mb-4">
            <ShieldCheck className="w-6 h-6 stroke-[1.75]" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
            Sign in to AutoRubric
          </h1>
          <p className="text-xs text-zinc-500 mt-1.5 max-w-xs">
            Autonomous rubric compilation, semantic evaluation, and adversarial security grading.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 text-xs text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="block text-xs font-medium text-zinc-600 mb-1.5 ml-1">
              Username
            </span>
            <input
              type="text"
              className="w-full px-4 py-2.5 rounded-xl bg-white/70 border border-black/[0.08] text-sm text-zinc-900 placeholder:text-zinc-400 focus:bg-white focus:border-zinc-900 focus:ring-4 focus:ring-zinc-900/5 outline-none transition-all duration-200"
              placeholder="admin@example.com"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>

          <label className="block">
            <span className="block text-xs font-medium text-zinc-600 mb-1.5 ml-1">
              Password
            </span>
            <input
              type="password"
              className="w-full px-4 py-2.5 rounded-xl bg-white/70 border border-black/[0.08] text-sm text-zinc-900 placeholder:text-zinc-400 focus:bg-white focus:border-zinc-900 focus:ring-4 focus:ring-zinc-900/5 outline-none transition-all duration-200"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-zinc-900 hover:bg-black text-white text-sm font-medium tracking-tight shadow-sm hover:shadow transition-all duration-200 disabled:opacity-50 active:scale-[0.99]"
            >
              <span>{isLoading ? 'Signing in...' : 'Sign In'}</span>
              {!isLoading && <ArrowRight className="w-4 h-4 stroke-[2]" />}
            </button>
          </div>
        </form>

        <div className="mt-8 pt-6 border-t border-black/[0.04] text-center">
          <span className="text-[11px] text-zinc-400">
            AutoRubric Security & Conformance Verified
          </span>
        </div>
      </div>
    </div>
  );
}
