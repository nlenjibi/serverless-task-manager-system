'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser } from 'aws-amplify/auth';
import { useAuthStore } from '@/store/auth.store';
import { getCurrentAuthUser } from '@/features/auth/services/auth.service';
import Navbar from '@/components/layout/Navbar';
import TaskList from '@/features/tasks/components/TaskList';

export default function DashboardPage() {
  const router = useRouter();
  const { user, setUser } = useAuthStore();

  useEffect(() => {
    getCurrentUser()
      .then(() => getCurrentAuthUser().then(setUser))
      .catch(() => router.push('/login'));
  }, [router, setUser]);

  if (!user) {
    return (
      <div className="loading-screen">
        <p>Loading…</p>
      </div>
    );
  }

  return (
    <>
      <Navbar />
      <main className="dashboard">
        <header className="dashboard__header">
          <h1 className="dashboard__title">My Tasks</h1>
          <p className="dashboard__subtitle">
            New tasks expire automatically after 5 minutes if not completed.
          </p>
        </header>
        <TaskList />
      </main>
    </>
  );
}
