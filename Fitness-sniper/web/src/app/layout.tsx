import type { Metadata } from 'next';
import { Toaster } from '@/components/ui/sonner';
import { Providers } from '@/components/providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'Fitness Sniper',
  description: 'Auto-book competitive fitness classes before they fill up',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body suppressHydrationWarning className="antialiased bg-black text-white">
        <a href="#main-content" className="skip-to-content">Skip to content</a>
        <Providers>
          <div id="main-content">{children}</div>
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
