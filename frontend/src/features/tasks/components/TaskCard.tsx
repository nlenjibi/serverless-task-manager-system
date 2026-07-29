'use client';

import { Task } from '@/types';
import { formatDate, statusColor, cn } from '@/lib/utils';

interface Props {
  task: Task;
  onComplete: (taskId: string) => void;
  onDelete: (taskId: string) => void;
}

export default function TaskCard({ task, onComplete, onDelete }: Props) {
  return (
    <div className="task-card">
      <div className="task-card__header">
        <p className="task-card__description">{task.Description || '(no description)'}</p>
        <span className={cn('status-badge', statusColor(task.Status))}>{task.Status}</span>
      </div>

      <div className="task-card__meta">
        <span>Date: {task.Date}</span>
        <span>Deadline: {formatDate(task.Deadline)}</span>
      </div>

      {task.Status === 'Pending' && (
        <div className="task-card__actions">
          <button
            onClick={() => onComplete(task.TaskId)}
            className="btn-success btn-sm"
          >
            Mark Complete
          </button>
          <button
            onClick={() => onDelete(task.TaskId)}
            className="btn-danger btn-sm"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}
