import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Auth state lives in localStorage (Amplify default) which is inaccessible in
// Edge middleware. Route protection is handled client-side in dashboard/page.tsx.
// This middleware only handles the login → dashboard redirect for UX clarity.
export function middleware(request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*'],
};
