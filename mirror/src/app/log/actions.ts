'use server';

import { revalidatePath } from 'next/cache';
import { createClient } from '@/lib/supabase/server';
import type { BreakoutZone } from '@/lib/types';

export interface SaveLogInput {
  date: string; // YYYY-MM-DD
  sleepHours: number | null;
  note: string | null;
  shineTzone: number | null;
  shineCheeks: number | null;
  breakoutCount: number | null;
  breakoutZones: BreakoutZone[];
  dryness: number | null;
  irritation: boolean;
  adherence: { stackItemId: string; taken: boolean }[];
}

export interface SaveLogResult {
  ok: boolean;
  error?: string;
}

export async function saveLog(input: SaveLogInput): Promise<SaveLogResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { ok: false, error: 'Not signed in.' };

  // Upsert the day's log (unique on user_id + date).
  const { data: logRow, error: logErr } = await supabase
    .from('logs')
    .upsert(
      {
        user_id: user.id,
        date: input.date,
        sleep_hours: input.sleepHours,
        note: input.note,
        shine_tzone: input.shineTzone,
        shine_cheeks: input.shineCheeks,
        breakout_count: input.breakoutCount,
        breakout_zones: input.breakoutZones,
        dryness: input.dryness,
        irritation: input.irritation,
      },
      { onConflict: 'user_id,date' },
    )
    .select('id')
    .single();

  if (logErr || !logRow) {
    return { ok: false, error: logErr?.message ?? 'Could not save log.' };
  }

  if (input.adherence.length > 0) {
    const { error: adhErr } = await supabase.from('log_adherence').upsert(
      input.adherence.map((a) => ({
        log_id: logRow.id,
        stack_item_id: a.stackItemId,
        user_id: user.id,
        taken: a.taken,
      })),
      { onConflict: 'log_id,stack_item_id' },
    );
    if (adhErr) return { ok: false, error: adhErr.message };
  }

  revalidatePath('/');
  revalidatePath('/log');
  return { ok: true };
}
