'use client';

import { useState, useEffect, useCallback } from 'react';
import { Task, CreateTaskPayload, UpdateTaskPayload } from '@/types';
import * as tasksService from '../services/tasks.service';

export function useTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await tasksService.fetchTasks();
      setTasks(data);
    } catch {
      setError('Failed to load tasks. Please refresh.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function create(payload: CreateTaskPayload) {
    const task = await tasksService.createTask(payload);
    setTasks((prev) => [task, ...prev]);
  }

  async function update(taskId: string, payload: UpdateTaskPayload) {
    const updated = await tasksService.updateTask(taskId, payload);
    setTasks((prev) => prev.map((t) => (t.TaskId === taskId ? updated : t)));
  }

  async function remove(taskId: string) {
    await tasksService.deleteTask(taskId);
    setTasks((prev) => prev.filter((t) => t.TaskId !== taskId));
  }

  return { tasks, loading, error, reload: load, create, update, remove };
}
