import { statusColor, formatDate } from '@/lib/utils';

describe('statusColor', () => {
  it('returns yellow classes for Pending', () => {
    expect(statusColor('Pending')).toContain('yellow');
  });
  it('returns green classes for Completed', () => {
    expect(statusColor('Completed')).toContain('green');
  });
  it('returns red classes for Expired', () => {
    expect(statusColor('Expired')).toContain('red');
  });
});

describe('formatDate', () => {
  it('returns a non-empty string for a valid ISO date', () => {
    const result = formatDate('2024-01-15T12:00:00.000Z');
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });
});
