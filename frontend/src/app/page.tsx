import { redirect } from 'next/navigation';

// Root page redirects based on auth state — handled client-side in dashboard
export default function Home() {
  redirect('/dashboard');
}
