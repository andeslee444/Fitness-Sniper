'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { LayoutDashboard, Target, CalendarDays, Clock, KeyRound, LogOut } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/schedule', label: 'Schedule', icon: CalendarDays },
  { href: '/targets', label: 'Targets', icon: Target },
  { href: '/history', label: 'History', icon: Clock },
  { href: '/credentials', label: 'Credentials', icon: KeyRound },
];

export function NavBar({ userEmail }: { userEmail: string }) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/');
  }

  return (
    <>
      {/* Desktop top nav */}
      <header className="hidden border-b border-white/10 sm:block">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="flex items-center gap-2 text-lg font-bold">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500 text-xs font-black text-black">FS</span>
              Fitness Sniper
            </Link>
            <nav className="flex gap-1">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-white/10 text-white'
                        : 'text-zinc-400 hover:bg-white/5 hover:text-white'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-zinc-500">{userEmail}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-zinc-400 hover:text-white"
            >
              <LogOut className="mr-1.5 h-4 w-4" />
              Log out
            </Button>
          </div>
        </div>
      </header>

      {/* Mobile top bar (logo + logout only) */}
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3 sm:hidden">
        <Link href="/dashboard" className="flex items-center gap-2 text-lg font-bold">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500 text-xs font-black text-black">FS</span>
          Fitness Sniper
        </Link>
        <Button variant="ghost" size="sm" onClick={handleLogout} className="text-zinc-400">
          <LogOut className="h-4 w-4" />
        </Button>
      </header>

      {/* Mobile bottom tab bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/10 bg-black/95 backdrop-blur-lg sm:hidden">
        <div className="flex items-center justify-around py-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  isActive
                    ? 'text-emerald-400'
                    : 'text-zinc-500'
                }`}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
