import { fetchTasks, createTask, updateTask, deleteTask } from '@/features/tasks/services/tasks.service';
import http from '@/lib/api';

jest.mock('@/lib/api');
const mockHttp = http as jest.Mocked<typeof http>;

const mockTask = {
  TaskId: 'abc-123',
  UserId: 'user-1',
  Description: 'Test task',
  Date: '2024-01-01',
  Status: 'Pending' as const,
  Deadline: '2024-01-01T00:05:00.000Z',
  CreatedAt: '2024-01-01T00:00:00.000Z',
  UpdatedAt: '2024-01-01T00:00:00.000Z',
};

describe('tasks.service', () => {
  afterEach(() => jest.clearAllMocks());

  it('fetchTasks returns task array', async () => {
    mockHttp.get = jest.fn().mockResolvedValue({ data: [mockTask] });
    const tasks = await fetchTasks();
    expect(tasks).toHaveLength(1);
    expect(tasks[0].TaskId).toBe('abc-123');
  });

  it('createTask posts payload and returns new task', async () => {
    mockHttp.post = jest.fn().mockResolvedValue({ data: mockTask });
    const task = await createTask({ description: 'Test task', date: '2024-01-01' });
    expect(mockHttp.post).toHaveBeenCalledWith('/tasks', { description: 'Test task', date: '2024-01-01' });
    expect(task.Status).toBe('Pending');
  });

  it('updateTask sends status update', async () => {
    const updated = { ...mockTask, Status: 'Completed' as const };
    mockHttp.put = jest.fn().mockResolvedValue({ data: updated });
    const task = await updateTask('abc-123', { status: 'Completed' });
    expect(task.Status).toBe('Completed');
  });

  it('deleteTask calls DELETE endpoint', async () => {
    mockHttp.delete = jest.fn().mockResolvedValue({});
    await deleteTask('abc-123');
    expect(mockHttp.delete).toHaveBeenCalledWith('/tasks/abc-123');
  });
});
