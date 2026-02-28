'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { CheckCircle, Plus, Trash2, Pencil } from 'lucide-react';

interface Props {
  studioSlug: string;
  studioName: string;
  hasSaved: boolean;
  validationStatus?: 'connected' | 'untested' | 'invalid' | 'checking';
}

export function CredentialForm({ studioSlug, studioName, hasSaved, validationStatus }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);

    try {
      const res = await fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ studioSlug, email, password }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Failed to save');
      }

      toast.success(`${studioName} credentials saved`);
      setEditing(false);
      setEmail('');
      setPassword('');
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save credentials');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Remove ${studioName} credentials? This cannot be undone.`)) return;

    try {
      const res = await fetch('/api/credentials', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ studioSlug }),
      });
      if (!res.ok) throw new Error('Failed to remove credentials');
      toast.success(`${studioName} credentials removed`);
      setEditing(false);
      router.refresh();
    } catch {
      toast.error('Failed to remove credentials');
    }
  }

  // Saved state — compact card
  if (hasSaved && !editing) {
    return (
      <div className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
        <div className="flex items-center gap-3">
          <CheckCircle className="h-4 w-4 text-emerald-400" />
          <span className="font-medium text-white">{studioName}</span>
          {/* Validation status badge */}
          {validationStatus === 'checking' && (
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-zinc-400">
              Checking...
            </span>
          )}
          {validationStatus === 'connected' && (
            <span className="rounded-full bg-emerald-950 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
              Connected
            </span>
          )}
          {validationStatus === 'untested' && (
            <span className="rounded-full bg-amber-950 px-2 py-0.5 text-[10px] font-medium text-amber-400">
              Untested
            </span>
          )}
          {validationStatus === 'invalid' && (
            <span className="rounded-full bg-red-950 px-2 py-0.5 text-[10px] font-medium text-red-400">
              Invalid
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => setEditing(true)} className="h-8 text-zinc-400 hover:text-white">
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDelete} className="h-8 text-zinc-400 hover:text-red-400">
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    );
  }

  // Unsaved — show "Add" button that expands to form
  if (!hasSaved && !editing) {
    return (
      <button
        onClick={() => setEditing(true)}
        className="flex items-center gap-3 rounded-xl border border-dashed border-white/10 px-4 py-3 text-left transition-colors hover:border-white/20 hover:bg-white/[0.02]"
      >
        <Plus className="h-4 w-4 text-zinc-500" />
        <span className="text-sm font-medium text-zinc-400">{studioName}</span>
      </button>
    );
  }

  // Editing form
  return (
    <div className="rounded-xl border border-emerald-500/20 bg-white/[0.02] p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-medium text-white">{studioName}</span>
        <Button variant="ghost" size="sm" onClick={() => { setEditing(false); setEmail(''); setPassword(''); }} className="h-7 text-xs text-zinc-400">
          Cancel
        </Button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1">
          <Label className="text-xs text-zinc-400">Email</Label>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={`your@${studioSlug}.com`}
            className="h-9 border-white/10 bg-white/5 text-sm text-white placeholder:text-zinc-600"
            required
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs text-zinc-400">Password</Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="h-9 border-white/10 bg-white/5 text-sm text-white placeholder:text-zinc-600"
            required
          />
        </div>
        <Button
          type="submit"
          size="sm"
          disabled={loading}
          className="w-full bg-emerald-500 text-black hover:bg-emerald-400"
        >
          {loading ? 'Saving...' : hasSaved ? 'Update' : 'Save Credentials'}
        </Button>
      </form>
    </div>
  );
}
