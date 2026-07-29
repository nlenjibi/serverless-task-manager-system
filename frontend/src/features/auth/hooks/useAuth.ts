'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/auth.store';
import * as authService from '../services/auth.service';

export function useLogin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setUser = useAuthStore((s) => s.setUser);
  const router = useRouter();

  async function handleLogin(email: string, password: string) {
    setLoading(true);
    setError(null);
    try {
      const user = await authService.login(email, password);
      setUser(user);
      router.push('/dashboard');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return { handleLogin, loading, error };
}

export function useRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleRegister(email: string, password: string) {
    setLoading(true);
    setError(null);
    try {
      await authService.register(email, password);
      // Auto-confirmed by PreSignUp Lambda — redirect straight to login
      router.push('/login?registered=true');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return { handleRegister, loading, error };
}

export function useLogout() {
  const setUser = useAuthStore((s) => s.setUser);
  const router = useRouter();

  async function handleLogout() {
    await authService.logout();
    setUser(null);
    router.push('/login');
  }

  return { handleLogout };
}
