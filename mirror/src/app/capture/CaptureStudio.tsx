'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { captureFrame } from '@/lib/image';
import { photoPath, PHOTO_BUCKET } from '@/lib/photos';
import { CAPTURE_CHECKLIST, LIGHTING_DELTA_THRESHOLD } from '@/lib/checklist';
import { ANGLES, ANGLE_LABEL, type PhotoAngle } from '@/lib/types';
import { saveSession, type CapturedPhoto } from './actions';

interface Shot {
  blob: Blob;
  width: number;
  height: number;
  luminance: number;
  previewUrl: string;
}

type Phase = 'checklist' | 'capture' | 'saving';

export function CaptureStudio({
  userId,
  ghosts,
  lastLighting,
}: {
  userId: string;
  ghosts: Partial<Record<PhotoAngle, string>>;
  lastLighting: number | null;
}) {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [phase, setPhase] = useState<Phase>('checklist');
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [angleIdx, setAngleIdx] = useState(0);
  const [shots, setShots] = useState<Partial<Record<PhotoAngle, Shot>>>({});
  const [ghostOpacity, setGhostOpacity] = useState(0.4);
  const [camError, setCamError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const angle = ANGLES[angleIdx];
  const allChecked = CAPTURE_CHECKLIST.every((c) => checked[c.id]);
  const shotCount = Object.keys(shots).length;

  // --- Camera lifecycle -----------------------------------------------------
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1080 }, height: { ideal: 1440 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setCamError(null);
    } catch {
      setCamError('Camera unavailable. Grant camera permission and use HTTPS.');
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    if (phase === 'capture') startCamera();
    return () => {
      if (phase !== 'capture') stopCamera();
    };
  }, [phase, startCamera, stopCamera]);

  useEffect(() => () => stopCamera(), [stopCamera]);

  // Revoke object URLs on unmount to avoid leaks.
  useEffect(() => {
    return () => {
      Object.values(shots).forEach((s) => s && URL.revokeObjectURL(s.previewUrl));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Capture --------------------------------------------------------------
  async function shoot() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const { blob, width, height, luminance } = await captureFrame(video);
    const previewUrl = URL.createObjectURL(blob);
    setShots((prev) => {
      const old = prev[angle];
      if (old) URL.revokeObjectURL(old.previewUrl);
      return { ...prev, [angle]: { blob, width, height, luminance, previewUrl } };
    });
  }

  function retake() {
    setShots((prev) => {
      const old = prev[angle];
      if (old) URL.revokeObjectURL(old.previewUrl);
      const next = { ...prev };
      delete next[angle];
      return next;
    });
  }

  // Lighting drift warning, computed from the front shot vs. last session.
  const frontShot = shots.front;
  const lightingDelta =
    frontShot && lastLighting != null
      ? Math.abs(frontShot.luminance - lastLighting)
      : null;
  const lightingWarn =
    lightingDelta != null && lightingDelta > LIGHTING_DELTA_THRESHOLD;

  // --- Save -----------------------------------------------------------------
  async function save() {
    setSaveError(null);
    setPhase('saving');
    stopCamera();

    const supabase = createClient();
    const sessionId =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.round(performance.now())}`;
    const capturedAt = new Date().toISOString();

    const uploaded: CapturedPhoto[] = [];
    for (const a of ANGLES) {
      const shot = shots[a];
      if (!shot) continue;
      const path = photoPath(userId, sessionId, a);
      const { error } = await supabase.storage
        .from(PHOTO_BUCKET)
        .upload(path, shot.blob, { contentType: 'image/jpeg', upsert: true });
      if (error) {
        setSaveError(`Upload failed for ${ANGLE_LABEL[a]}: ${error.message}`);
        setPhase('capture');
        startCamera();
        return;
      }
      uploaded.push({ angle: a, storage_path: path, width: shot.width, height: shot.height });
    }

    const lightingScore = frontShot ? Math.round(frontShot.luminance * 100) / 100 : null;
    const res = await saveSession({
      sessionId,
      capturedAt,
      lightingScore,
      notes: null,
      photos: uploaded,
    });

    if (!res.ok) {
      setSaveError(res.error ?? 'Could not save session.');
      setPhase('capture');
      startCamera();
      return;
    }
    router.push('/compare');
    router.refresh();
  }

  // --- Render ---------------------------------------------------------------
  if (phase === 'checklist') {
    return (
      <main className="space-y-6">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight">New session</h1>
          <p className="text-sm text-mute">
            Consistency is the whole trick. Confirm each item so this session is
            comparable to the last.
          </p>
        </header>

        <ul className="card space-y-1">
          {CAPTURE_CHECKLIST.map((c) => (
            <li key={c.id}>
              <label className="flex cursor-pointer items-center gap-3 rounded-lg px-1 py-2.5">
                <input
                  type="checkbox"
                  className="h-5 w-5 accent-accent"
                  checked={!!checked[c.id]}
                  onChange={(e) =>
                    setChecked((prev) => ({ ...prev, [c.id]: e.target.checked }))
                  }
                />
                <span className="text-sm">{c.label}</span>
              </label>
            </li>
          ))}
        </ul>

        <button
          className="btn-primary w-full"
          disabled={!allChecked}
          onClick={() => setPhase('capture')}
        >
          {allChecked ? 'Start capture' : 'Confirm all items to continue'}
        </button>
      </main>
    );
  }

  const ghost = ghosts[angle];
  const currentShot = shots[angle];

  return (
    <main className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{ANGLE_LABEL[angle]}</h1>
          <p className="text-xs text-mute">
            Angle {angleIdx + 1} of {ANGLES.length} · {shotCount} captured
          </p>
        </div>
        {ghost && !currentShot && (
          <label className="text-right text-[11px] text-mute">
            Ghost
            <input
              type="range"
              min={0}
              max={0.8}
              step={0.05}
              value={ghostOpacity}
              onChange={(e) => setGhostOpacity(Number(e.target.value))}
              className="ml-2 w-24 align-middle accent-accent"
            />
          </label>
        )}
      </header>

      <div className="relative mx-auto aspect-[3/4] w-full max-w-sm overflow-hidden rounded-2xl border border-edge bg-black">
        {/* Live camera */}
        {!currentShot && (
          <video
            ref={videoRef}
            playsInline
            muted
            className="h-full w-full object-cover"
          />
        )}

        {/* Ghost overlay from last session — the alignment trick */}
        {ghost && !currentShot && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={ghost}
            alt=""
            aria-hidden
            className="pointer-events-none absolute inset-0 h-full w-full object-cover mix-blend-screen"
            style={{ opacity: ghostOpacity }}
          />
        )}

        {/* Captured preview */}
        {currentShot && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={currentShot.previewUrl}
            alt={`${ANGLE_LABEL[angle]} preview`}
            className="h-full w-full object-cover"
          />
        )}

        {/* Center guide line for profile alignment */}
        {!currentShot && !ghost && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="h-3/4 w-px bg-white/20" />
          </div>
        )}
      </div>

      {camError && (
        <p className="rounded-xl bg-red-950/50 px-3 py-2 text-xs text-red-300">
          {camError}
        </p>
      )}

      {lightingWarn && (
        <p className="rounded-xl bg-amber-950/50 px-3 py-2 text-xs text-amber-300">
          Lighting looks different from your last session (Δ
          {Math.round(lightingDelta!)} brightness). Try to match it, or the
          comparison will be muddy.
        </p>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3">
        {!currentShot ? (
          <button className="btn-primary flex-1" onClick={shoot} disabled={!!camError}>
            Capture
          </button>
        ) : (
          <button className="btn-ghost flex-1" onClick={retake}>
            Retake
          </button>
        )}

        {angleIdx < ANGLES.length - 1 ? (
          <button
            className="btn-ghost flex-1"
            onClick={() => setAngleIdx((i) => Math.min(i + 1, ANGLES.length - 1))}
          >
            Next angle →
          </button>
        ) : (
          <button
            className="btn-primary flex-1"
            onClick={save}
            disabled={shotCount === 0}
          >
            Save session
          </button>
        )}
      </div>

      <div className="flex items-center justify-between">
        <button
          className="text-xs text-mute disabled:opacity-40"
          onClick={() => setAngleIdx((i) => Math.max(i - 1, 0))}
          disabled={angleIdx === 0}
        >
          ← Previous
        </button>
        {shotCount > 0 && angleIdx < ANGLES.length - 1 && (
          <button className="text-xs text-accent" onClick={save}>
            Save {shotCount} now
          </button>
        )}
      </div>

      {saveError && <p className="text-xs text-red-400">{saveError}</p>}

      {phase === 'saving' && (
        <p className="text-center text-sm text-mute">Uploading…</p>
      )}
    </main>
  );
}
