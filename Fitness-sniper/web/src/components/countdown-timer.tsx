'use client';

import { useState, useEffect } from 'react';
import { Timer } from 'lucide-react';

interface CountdownTimerProps {
  scheduledFor: string; // ISO datetime
}

function formatRemaining(ms: number): string {
  if (ms <= 0) return '';

  const totalSeconds = Math.floor(ms / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days >= 1) {
    return `${days}d ${hours}h`;
  }
  if (hours >= 1) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m ${seconds}s`;
}

export function CountdownTimer({ scheduledFor }: CountdownTimerProps) {
  const target = new Date(scheduledFor).getTime();

  const [remaining, setRemaining] = useState(() => target - Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining(target - Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, [target]);

  const attemptTime = new Date(scheduledFor).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/New_York',
  });

  if (remaining <= 0) {
    return (
      <span className="flex items-center gap-1 text-xs text-zinc-400">
        <Timer className="h-3 w-3" />
        Attempting now...
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 text-xs text-zinc-400">
      <Timer className="h-3 w-3" />
      Booking opens in {formatRemaining(remaining)} — we&apos;ll attempt at {attemptTime} ET
    </span>
  );
}
