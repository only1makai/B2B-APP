'use server';

import { revalidatePath } from 'next/cache';
import { createClient } from '@/lib/supabase/server';
import type { StackSchedule } from '@/lib/types';

export async function addStackItem(input: {
  productName: string;
  category: string | null;
  schedule: StackSchedule;
  startedAt: string;
}): Promise<{ ok: boolean; error?: string }> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { ok: false, error: 'Not signed in.' };
  if (!input.productName.trim()) return { ok: false, error: 'Name required.' };

  const { error } = await supabase.from('stack_items').insert({
    user_id: user.id,
    product_name: input.productName.trim(),
    category: input.category?.trim() || null,
    schedule: input.schedule,
    started_at: input.startedAt,
  });
  if (error) return { ok: false, error: error.message };
  revalidatePath('/stack');
  revalidatePath('/log');
  return { ok: true };
}

export async function endStackItem(
  id: string,
  endedAt: string,
): Promise<{ ok: boolean; error?: string }> {
  const supabase = await createClient();
  const { error } = await supabase
    .from('stack_items')
    .update({ ended_at: endedAt })
    .eq('id', id);
  if (error) return { ok: false, error: error.message };
  revalidatePath('/stack');
  revalidatePath('/log');
  return { ok: true };
}

export async function deleteStackItem(
  id: string,
): Promise<{ ok: boolean; error?: string }> {
  const supabase = await createClient();
  const { error } = await supabase.from('stack_items').delete().eq('id', id);
  if (error) return { ok: false, error: error.message };
  revalidatePath('/stack');
  revalidatePath('/log');
  return { ok: true };
}
