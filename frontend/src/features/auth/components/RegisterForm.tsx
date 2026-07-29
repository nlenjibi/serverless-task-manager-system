'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRegister } from '../hooks/useAuth';

export default function RegisterForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const { handleRegister, loading, error } = useRegister();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setValidationError('Passwords do not match');
      return;
    }
    setValidationError(null);
    handleRegister(email, password);
  };

  return (
    <div className="auth-card">
      <h1 className="auth-title">Create account</h1>

      {(error || validationError) && (
        <p className="error-banner">{validationError ?? error}</p>
      )}

      <form onSubmit={onSubmit} className="auth-form">
        <label className="field-label">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="field-input"
            placeholder="you@example.com"
          />
        </label>

        <label className="field-label">
          Password
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="field-input"
            placeholder="Min. 8 characters"
          />
        </label>

        <label className="field-label">
          Confirm password
          <input
            type="password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="field-input"
            placeholder="Repeat password"
          />
        </label>

        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="auth-switch">
        Already have an account?{' '}
        <Link href="/login" className="auth-link">
          Sign in
        </Link>
      </p>
    </div>
  );
}
