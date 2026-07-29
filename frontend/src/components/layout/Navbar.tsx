'use client';

import Link from 'next/link';
import { useAuthStore } from '@/store/auth.store';
import { useLogout } from '@/features/auth/hooks/useAuth';

export default function Navbar() {
  const user = useAuthStore((s) => s.user);
  const { handleLogout } = useLogout();

  return (
    <nav className="navbar">
      <Link href="/dashboard" className="navbar__brand">
        ✅ Todo App
      </Link>

      <div className="navbar__right">
        {user && (
          <>
            <span className="navbar__email">{user.email}</span>
            <button onClick={handleLogout} className="btn-secondary btn-sm">
              Sign out
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
