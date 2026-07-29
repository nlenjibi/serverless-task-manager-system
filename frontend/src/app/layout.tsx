import type { Metadata } from 'next';
import './globals.css';
import AmplifyProvider from './AmplifyProvider';

export const metadata: Metadata = {
  title: 'Serverless Todo App',
  description: 'Event-driven task management powered by AWS',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AmplifyProvider>{children}</AmplifyProvider>
      </body>
    </html>
  );
}
