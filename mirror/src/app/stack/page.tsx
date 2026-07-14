import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { localDateString } from '@/lib/date';
import type { StackItem } from '@/lib/types';
import { StackManager } from './StackManager';

export const dynamic = 'force-dynamic';

export default async function StackPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const { data } = await supabase
    .from('stack_items')
    .select('*')
    .order('started_at', { ascending: false });

  const items = (data ?? []) as StackItem[];
  return <StackManager items={items} today={localDateString()} />;
}
