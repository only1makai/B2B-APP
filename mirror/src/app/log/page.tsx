import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { localDateString } from '@/lib/date';
import type { Log, StackItem, LogAdherence } from '@/lib/types';
import { LogForm } from './LogForm';

export const dynamic = 'force-dynamic';

export default async function LogPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const params = await searchParams;
  const date = params.date ?? localDateString();

  const { data: log } = await supabase
    .from('logs')
    .select('*')
    .eq('date', date)
    .maybeSingle();

  const existing = (log as Log | null) ?? null;

  // Active stack items (no end date, or end date in the future) for adherence.
  const { data: stack } = await supabase
    .from('stack_items')
    .select('*')
    .or(`ended_at.is.null,ended_at.gte.${date}`)
    .lte('started_at', date)
    .order('started_at', { ascending: true });

  const stackItems = (stack ?? []) as StackItem[];

  let adherence: LogAdherence[] = [];
  if (existing) {
    const { data: adh } = await supabase
      .from('log_adherence')
      .select('*')
      .eq('log_id', existing.id);
    adherence = (adh ?? []) as LogAdherence[];
  }

  return (
    <LogForm
      date={date}
      existing={existing}
      stackItems={stackItems}
      adherence={adherence}
    />
  );
}
