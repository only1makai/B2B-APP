import type { Metadata, Viewport } from 'next';
import './globals.css';
import { NavBar } from '@/components/NavBar';
import { ServiceWorker } from '@/components/ServiceWorker';

export const metadata: Metadata = {
  title: 'Mirror',
  description: 'Track what actually changes: skin, hair, sleep — and what worked.',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Mirror',
  },
};

export const viewport: Viewport = {
  themeColor: '#0d0f12',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 pb-24 pt-6">
          {children}
        </div>
        <NavBar />
        <ServiceWorker />
      </body>
    </html>
  );
}
