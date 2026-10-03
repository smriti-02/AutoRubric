'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && pathname !== '/login') {
      const stored = typeof window !== 'undefined' ? (sessionStorage.getItem('token') || localStorage.getItem('token')) : null;
      if (!token && !stored) {
        router.push('/login');
      }
    }
  }, [mounted, token, pathname, router]);

  if (!mounted) return null; // Avoid hydration mismatch

  const hasToken = token || (typeof window !== 'undefined' && (sessionStorage.getItem('token') || localStorage.getItem('token')));
  if (!hasToken && pathname !== '/login') {
    return null; // Wait for redirect
  }

  return <>{children}</>;
}
