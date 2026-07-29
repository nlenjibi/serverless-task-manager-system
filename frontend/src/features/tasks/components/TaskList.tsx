'use client';

import { useState } from 'react';
import { Task, TaskStatus } from '@/types';
import { useTasks } from '../hooks/useTasks';
import TaskCard from './TaskCard';
import CreateTaskModal from './CreateTaskModal';

const TABS: TaskStatus[] = ['Pending', 'Completed', 'Expired'];

export default function TaskList() {
  const { tasks, loading, error, create, update, remove, reload } = useTasks();
  const [activeTab, setActiveTab] = useState<TaskStatus>('Pending');
  const [showModal, setShowModal] = useState(false);

  const filtered = tasks.filter((t) => t.Status === activeTab);

  const handleComplete = async (taskId: string) => {
    await update(taskId, { status: 'Completed' });
  };

  const handleDelete = async (taskId: string) => {
    await remove(taskId);
  };

  return (
    <div className="task-list-container">
      {/* Tab bar */}
      <div className="tabs">
        {TABS.map((tab) => {
          const count = tasks.filter((t) => t.Status === tab).length;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`tab ${activeTab === tab ? 'tab--active' : ''}`}
            >
              {tab}
              {count > 0 && <span className="tab__badge">{count}</span>}
            </button>
          );
        })}
      </div>

      {/* Toolbar */}
      <div className="toolbar">
        <button onClick={reload} className="btn-secondary btn-sm">
          Refresh
        </button>
        <button onClick={() => setShowModal(true)} className="btn-primary">
          + New Task
        </button>
      </div>

      {/* Content */}
      {loading && <p className="state-message">Loading tasks…</p>}
      {error && <p className="error-banner">{error}</p>}

      {!loading && !error && filtered.length === 0 && (
        <p className="state-message">No {activeTab.toLowerCase()} tasks.</p>
      )}

      <div className="task-grid">
        {filtered.map((task) => (
          <TaskCard
            key={task.TaskId}
            task={task}
            onComplete={handleComplete}
            onDelete={handleDelete}
          />
        ))}
      </div>

      {showModal && (
        <CreateTaskModal
          onClose={() => setShowModal(false)}
          onCreate={create}
        />
      )}
    </div>
  );
}
