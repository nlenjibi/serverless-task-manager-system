'use client';

import { useState } from 'react';
import { CreateTaskPayload } from '@/types';

interface Props {
  onClose: () => void;
  onCreate: (payload: CreateTaskPayload) => Promise<void>;
}

export default function CreateTaskModal({ onClose, onCreate }: Props) {
  const today = new Date().toISOString().split('T')[0];
  const [description, setDescription] = useState('');
  const [date, setDate] = useState(today);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await onCreate({ description: description.trim(), date });
      onClose();
    } catch {
      setError('Failed to create task. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal__title">New Task</h2>
        <p className="modal__subtitle">
          Tasks automatically expire after <strong>5 minutes</strong> if not completed.
        </p>

        {error && <p className="error-banner">{error}</p>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field-label">
            Description
            <textarea
              required
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="field-input"
              placeholder="What needs to be done?"
            />
          </label>

          <label className="field-label">
            Date
            <input
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="field-input"
            />
          </label>

          <div className="modal__actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="btn-primary">
              {submitting ? 'Creating…' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
