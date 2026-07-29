import RegisterForm from '@/features/auth/components/RegisterForm';

export const metadata = { title: 'Create account — Todo App' };

export default function RegisterPage() {
  return (
    <main className="auth-page">
      <RegisterForm />
    </main>
  );
}
