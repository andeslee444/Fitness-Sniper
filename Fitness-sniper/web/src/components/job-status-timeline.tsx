'use client';

import { AlertCircle } from 'lucide-react';
import type { JobStatus } from '@/lib/types';

interface TimelineProps {
  jobStatus: JobStatus | null;
  scheduledFor: string | null;
  classDatetime: string | null;
  createdAt: string | null;
  claimedAt: string | null;
  message: string | null;
}

export function translateJobMessage(raw: string | null): string {
  if (!raw) return 'An unknown error occurred';
  const lower = raw.toLowerCase();
  if (lower.includes('no credentials') || lower.includes('authentication failed') || lower.includes('login'))
    return 'Credential check failed — update your password in Credentials';
  if (lower.includes('full') || lower.includes('no available spots'))
    return 'Class was full when we attempted';
  if (lower.includes('class not found') || lower.includes('not in schedule'))
    return "Class wasn't on the schedule yet";
  if (lower.includes('target not found'))
    return 'Snipe target was removed';
  return raw;
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/New_York',
  });
}

function formatScheduledFor(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: 'America/New_York',
  });
}

/** Maps JobStatus to active step index (0-3). null = step 0. */
function deriveActiveStep(status: JobStatus | null): number {
  switch (status) {
    case null:
      return 0;
    case 'pending':
      return 1;
    case 'claimed':
    case 'running':
      return 2;
    case 'success':
    case 'failed':
    case 'cancelled':
      return 3;
    default:
      return 0;
  }
}

interface StepConfig {
  label: string;
  timestamp: string | null;
  sublabel?: string;
}

export function JobStatusTimeline({
  jobStatus,
  scheduledFor,
  createdAt,
  claimedAt,
  message,
}: TimelineProps) {
  if (jobStatus === null) return null;

  const activeStep = deriveActiveStep(jobStatus);

  const steps: StepConfig[] = [
    {
      label: 'Scheduled',
      timestamp: createdAt ? formatTimestamp(createdAt) : null,
    },
    {
      label: 'Waiting',
      timestamp: null,
      sublabel: scheduledFor ? `Opens ${formatScheduledFor(scheduledFor)} ET` : undefined,
    },
    {
      label: 'Attempting',
      timestamp: claimedAt ? formatTimestamp(claimedAt) : null,
    },
    {
      label: jobStatus === 'success' ? 'Booked' : jobStatus === 'cancelled' ? 'Cancelled' : 'Result',
      timestamp: null,
    },
  ];

  return (
    <div className="mt-2">
      {/* Step circles + connecting lines */}
      <div className="flex items-center">
        {steps.map((step, idx) => {
          const isCompleted = idx < activeStep;
          const isActive = idx === activeStep;
          const isFailed = isActive && idx === 3 && jobStatus === 'failed';
          const isCancelled = isActive && idx === 3 && jobStatus === 'cancelled';
          const isSuccess = isActive && idx === 3 && jobStatus === 'success';

          return (
            <div key={step.label} className="flex flex-1 items-center">
              {/* Circle */}
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-5 w-5 items-center justify-center rounded-full border-2 transition-colors ${
                    isFailed
                      ? 'border-red-400 bg-red-400/20'
                      : isSuccess
                        ? 'border-emerald-400 bg-emerald-400/20'
                        : isCancelled
                          ? 'border-zinc-500 bg-zinc-700'
                          : isCompleted
                            ? 'border-emerald-400 bg-emerald-400'
                            : isActive
                              ? 'animate-pulse border-blue-400 bg-blue-400/30'
                              : 'border-zinc-700 bg-zinc-800'
                  }`}
                >
                  {isFailed && <AlertCircle className="h-3 w-3 text-red-400" />}
                  {isCompleted && (
                    <svg className="h-2.5 w-2.5 text-zinc-900" fill="currentColor" viewBox="0 0 12 12">
                      <path d="M1 6l3.5 3.5L11 2" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
              </div>

              {/* Connecting line (not after last step) */}
              {idx < steps.length - 1 && (
                <div
                  className={`h-0.5 flex-1 transition-colors ${
                    idx < activeStep ? 'bg-emerald-400' : 'bg-zinc-700'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Step labels below circles */}
      <div className="mt-1 flex">
        {steps.map((step, idx) => {
          const isCompleted = idx < activeStep;
          const isActive = idx === activeStep;
          const isFailed = isActive && idx === 3 && jobStatus === 'failed';

          return (
            <div key={step.label} className="flex flex-1 flex-col items-center text-center">
              <span
                className={`text-xs ${
                  isFailed
                    ? 'font-medium text-red-400'
                    : isCompleted
                      ? 'text-emerald-400'
                      : isActive
                        ? 'text-white'
                        : 'text-zinc-600'
                }`}
              >
                {step.label}
              </span>
              {step.timestamp && (
                <span className="mt-0.5 text-xs text-zinc-500">{step.timestamp}</span>
              )}
              {step.sublabel && isActive && (
                <span className="mt-0.5 text-xs text-zinc-500">{step.sublabel}</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Prominent failure message */}
      {jobStatus === 'failed' && message && (
        <div className="mt-2 flex items-start gap-1.5">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
          <span className="text-sm text-red-400">{translateJobMessage(message)}</span>
        </div>
      )}
    </div>
  );
}
