'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

interface Props {
  studioSlug: string;
  studioName: string;
  hasSaved: boolean;
}

export function CredentialForm({ studioSlug, studioName, hasSaved }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(!hasSaved);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);

    try {
      // Encrypt on the server via API route
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
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();
    await supabase
      .from('studio_credentials')
      .delete()
      .eq('user_id', user!.id)
      .eq('studio_slug', studioSlug);
    toast.success(`${studioName} credentials removed`);
    setEditing(true);
    router.refresh();
  }

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base text-white">{studioName}</CardTitle>
        {hasSaved && !editing && (
          <Badge variant="outline" className="border-green-500/30 text-green-400">
            Saved
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        {editing ? (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1">
              <Label className="text-xs">Email</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={`${studioSlug}@example.com`}
                className="border-zinc-700 bg-zinc-900"
                required
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Password</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="border-zinc-700 bg-zinc-900"
                required
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="sm" disabled={loading} className="flex-1">
                {loading ? 'Saving...' : 'Save'}
              </Button>
              {hasSaved && (
                <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        ) : (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing(true)} className="flex-1 border-zinc-700">
              Update
            </Button>
            <Button variant="ghost" size="sm" onClick={handleDelete} className="text-red-400">
              Remove
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
