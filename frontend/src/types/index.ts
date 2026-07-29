export type TaskStatus = 'Pending' | 'Completed' | 'Expired';

export interface Task {
  TaskId: string;
  UserId: string;
  Description: string;
  Date: string;
  Status: TaskStatus;
  Deadline: string;
  CreatedAt: string;
  UpdatedAt: string;
  UserEmail?: string;
}

export interface CreateTaskPayload {
  description: string;
  date: string;
}

export interface UpdateTaskPayload {
  description?: string;
  date?: string;
  status?: 'Pending' | 'Completed';
}

export interface AuthUser {
  sub: string;
  email: string;
  idToken: string;
}
