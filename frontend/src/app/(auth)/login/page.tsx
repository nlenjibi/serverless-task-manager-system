import LoginForm from '@/features/auth/components/LoginForm';

export const metadata = { title: 'Sign in — Todo App' };

export default function LoginPage() {
  return (
    <main className="auth-page">
      <LoginForm />
    </main>
  );
}
