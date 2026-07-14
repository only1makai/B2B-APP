// Hand-written DB types mirroring supabase/migrations/0001_init.sql.
// Regenerate with `supabase gen types typescript` once the CLI is wired up.

export type PhotoAngle = 'front' | 'left' | 'right';
export type StackSchedule = 'am' | 'pm' | 'both';

export const ANGLES: PhotoAngle[] = ['front', 'left', 'right'];

export const ANGLE_LABEL: Record<PhotoAngle, string> = {
  front: 'Front',
  left: 'Left profile',
  right: 'Right profile',
};

export interface Session {
  id: string;
  user_id: string;
  captured_at: string;
  lighting_score: number | null;
  notes: string | null;
  created_at: string;
}

export interface Photo {
  id: string;
  session_id: string;
  user_id: string;
  angle: PhotoAngle;
  storage_path: string;
  width: number | null;
  height: number | null;
  created_at: string;
}

export interface Log {
  id: string;
  user_id: string;
  date: string; // YYYY-MM-DD
  sleep_hours: number | null;
  note: string | null;
  shine_tzone: number | null;
  shine_cheeks: number | null;
  breakout_count: number | null;
  breakout_zones: BreakoutZone[];
  dryness: number | null;
  irritation: boolean;
  created_at: string;
  updated_at: string;
}

// A tap on the face map, normalized 0..1 within the face graphic.
export interface BreakoutZone {
  x: number;
  y: number;
}

export interface StackItem {
  id: string;
  user_id: string;
  product_name: string;
  category: string | null;
  started_at: string; // YYYY-MM-DD
  ended_at: string | null;
  schedule: StackSchedule;
  created_at: string;
}

export interface LogAdherence {
  log_id: string;
  stack_item_id: string;
  user_id: string;
  taken: boolean;
}

// A session joined with its photos, the shape most UI works with.
export interface SessionWithPhotos extends Session {
  photos: Photo[];
}
