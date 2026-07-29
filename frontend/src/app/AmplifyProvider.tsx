'use client';

import { useEffect } from 'react';
import { configureAmplify } from '@/lib/amplify-config';

configureAmplify();

export default function AmplifyProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Amplify is configured at module load time above; this effect is a no-op
    // but ensures the module is imported client-side before any auth calls.
  }, []);

  return <>{children}</>;
}
