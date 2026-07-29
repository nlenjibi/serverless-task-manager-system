import http from '@/lib/api';
import { Task, CreateTaskPayload, UpdateTaskPayload } from '@/types';

export async function fetchTasks(): Promise<Task[]> {
  const { data } = await http.get<Task[]>('/tasks');
  return data;
}

export async function createTask(payload: CreateTaskPayload): Promise<Task> {
  const { data } = await http.post<Task>('/tasks', payload);
  return data;
}

export async function updateTask(taskId: string, payload: UpdateTaskPayload): Promise<Task> {
  const { data } = await http.put<Task>(`/tasks/${taskId}`, payload);
  return data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await http.delete(`/tasks/${taskId}`);
}
