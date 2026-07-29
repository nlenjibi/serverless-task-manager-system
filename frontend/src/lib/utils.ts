import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function statusColor(status: string): string {
  switch (status) {
    case 'Pending':
      return 'text-yellow-700 bg-yellow-100';
    case 'Completed':
      return 'text-green-700 bg-green-100';
    case 'Expired':
      return 'text-red-700 bg-red-100';
    default:
      return 'text-gray-700 bg-gray-100';
  }
}
