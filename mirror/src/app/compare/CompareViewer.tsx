'use client';

import { useMemo, useState, useRef } from 'react';
import { ANGLES, ANGLE_LABEL, type PhotoAngle } from '@/lib/types';
import { prettyDate, daysBetween } from '@/lib/date';

export interface CompareSession {
  id: string;
  capturedAt: string;
  photos: Partial<Record<PhotoAngle, string>>;
}

type Mode = 'slider' | 'side';

export function CompareViewer({ sessions }: { sessions: CompareSession[] }) {
  // sessions arrive oldest -> newest.
  const [angle, setAngle] = useState<PhotoAngle>('front');
  const [mode, setMode] = useState<Mode>('slider');
  const [aIdx, setAIdx] = useState(0);
  const [bIdx, setBIdx] = useState(sessions.length - 1);
  const [split, setSplit] = useState(50);
  const [exportUrl, setExportUrl] = useState<string | null>(null);
  const [exportErr, setExportErr] = useState<string | null>(null);

  const a = sessions[aIdx];
  const b = sessions[bIdx];
  const aUrl = a?.photos[angle];
  const bUrl = b?.photos[angle];

  // Which angles exist in at least one of the two selected sessions.
  const availableAngles = useMemo(
    () => ANGLES.filter((ang) => sessions.some((s) => s.photos[ang])),
    [sessions],
  );

  const span =
    a && b ? Math.abs(daysBetween(a.capturedAt, b.capturedAt)) : 0;

  return (
    <main className="space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Compare</h1>
        <div className="flex rounded-xl border border-edge p-0.5 text-xs">
          {(['slider', 'side'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-lg px-3 py-1.5 ${
                mode === m ? 'bg-accent text-ink' : 'text-mute'
              }`}
            >
              {m === 'slider' ? 'Slider' : 'Side by side'}
            </button>
          ))}
        </div>
      </header>

      {/* Angle selector */}
      <div className="flex gap-2">
        {availableAngles.map((ang) => (
          <button
            key={ang}
            onClick={() => setAngle(ang)}
            className={`flex-1 rounded-xl border px-3 py-2 text-xs ${
              angle === ang
                ? 'border-accent text-accent'
                : 'border-edge text-mute'
            }`}
          >
            {ANGLE_LABEL[ang]}
          </button>
        ))}
      </div>

      {span > 0 && (
        <p className="text-center text-xs text-mute">
          {span} days apart · {prettyDate(a.capturedAt)} → {prettyDate(b.capturedAt)}
        </p>
      )}

      {/* Viewer */}
      {!aUrl || !bUrl ? (
        <div className="card text-center text-sm text-mute">
          One of the selected sessions has no {ANGLE_LABEL[angle].toLowerCase()}{' '}
          photo. Pick another angle or session.
        </div>
      ) : mode === 'slider' ? (
        <SliderView aUrl={aUrl} bUrl={bUrl} split={split} onSplit={setSplit} />
      ) : (
        <SideView aUrl={aUrl} bUrl={bUrl} aLabel={prettyDate(a.capturedAt)} bLabel={prettyDate(b.capturedAt)} />
      )}

      {/* Timeline scrub */}
      <div className="card space-y-4">
        <div>
          <div className="mb-1 flex justify-between text-[11px] text-mute">
            <span>A · {a ? prettyDate(a.capturedAt) : '—'}</span>
            <span>oldest → newest</span>
          </div>
          <input
            type="range"
            min={0}
            max={sessions.length - 1}
            value={aIdx}
            onChange={(e) => setAIdx(Number(e.target.value))}
            className="w-full accent-accent"
          />
        </div>
        <div>
          <div className="mb-1 flex justify-between text-[11px] text-mute">
            <span>B · {b ? prettyDate(b.capturedAt) : '—'}</span>
            <span>{sessions.length} sessions</span>
          </div>
          <input
            type="range"
            min={0}
            max={sessions.length - 1}
            value={bIdx}
            onChange={(e) => setBIdx(Number(e.target.value))}
            className="w-full accent-accent"
          />
        </div>
      </div>

      {/* Export */}
      <ExportControls
        aUrl={aUrl}
        bUrl={bUrl}
        aLabel={a ? prettyDate(a.capturedAt) : ''}
        bLabel={b ? prettyDate(b.capturedAt) : ''}
        angleLabel={ANGLE_LABEL[angle]}
        exportUrl={exportUrl}
        setExportUrl={setExportUrl}
        exportErr={exportErr}
        setExportErr={setExportErr}
      />
    </main>
  );
}

function SliderView({
  aUrl,
  bUrl,
  split,
  onSplit,
}: {
  aUrl: string;
  bUrl: string;
  split: number;
  onSplit: (n: number) => void;
}) {
  return (
    <div>
      <div className="relative mx-auto aspect-[3/4] w-full max-w-sm select-none overflow-hidden rounded-2xl border border-edge bg-black">
        {/* B is the base (newest) */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={bUrl} alt="B" className="absolute inset-0 h-full w-full object-cover" />
        {/* A clipped from the left */}
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ width: `${split}%` }}
        >
          {/* Inner image keeps the FULL container width so it stays aligned
              with the base image behind it; the parent div does the clipping. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={aUrl}
            alt="A"
            className="h-full max-w-none object-cover"
            style={{ width: split > 0 ? `${(100 / split) * 100}%` : '100%' }}
          />
        </div>
        {/* Divider */}
        <div
          className="absolute inset-y-0 w-0.5 bg-accent"
          style={{ left: `${split}%` }}
        />
        <span className="absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-[10px]">
          A
        </span>
        <span className="absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-[10px]">
          B
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={split}
        onChange={(e) => onSplit(Number(e.target.value))}
        className="mt-3 w-full accent-accent"
        aria-label="Comparison split"
      />
    </div>
  );
}

function SideView({
  aUrl,
  bUrl,
  aLabel,
  bLabel,
}: {
  aUrl: string;
  bUrl: string;
  aLabel: string;
  bLabel: string;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {[
        { url: aUrl, label: aLabel },
        { url: bUrl, label: bLabel },
      ].map((it, i) => (
        <figure key={i} className="space-y-1">
          <div className="aspect-[3/4] overflow-hidden rounded-xl border border-edge bg-black">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={it.url} alt={it.label} className="h-full w-full object-cover" />
          </div>
          <figcaption className="text-center text-[11px] text-mute">
            {it.label}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

function ExportControls({
  aUrl,
  bUrl,
  aLabel,
  bLabel,
  angleLabel,
  exportUrl,
  setExportUrl,
  exportErr,
  setExportErr,
}: {
  aUrl?: string;
  bUrl?: string;
  aLabel: string;
  bLabel: string;
  angleLabel: string;
  exportUrl: string | null;
  setExportUrl: (u: string | null) => void;
  exportErr: string | null;
  setExportErr: (e: string | null) => void;
}) {
  const [busy, setBusy] = useState(false);
  const linkRef = useRef<HTMLAnchorElement>(null);

  async function loadImage(src: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error('image load failed'));
      img.src = src;
    });
  }

  async function buildExport() {
    if (!aUrl || !bUrl) return;
    setBusy(true);
    setExportErr(null);
    try {
      const [ia, ib] = await Promise.all([loadImage(aUrl), loadImage(bUrl)]);
      const cellW = 600;
      const cellH = 800;
      const pad = 24;
      const footer = 64;
      const canvas = document.createElement('canvas');
      canvas.width = cellW * 2 + pad * 3;
      canvas.height = cellH + pad * 2 + footer;
      const ctx = canvas.getContext('2d')!;
      ctx.fillStyle = '#0d0f12';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      drawCover(ctx, ia, pad, pad, cellW, cellH);
      drawCover(ctx, ib, pad * 2 + cellW, pad, cellW, cellH);

      ctx.fillStyle = '#8b95a3';
      ctx.font = '24px ui-sans-serif, system-ui, sans-serif';
      ctx.textBaseline = 'middle';
      const y = pad + cellH + footer / 2;
      ctx.textAlign = 'left';
      ctx.fillText(aLabel, pad, y);
      ctx.textAlign = 'right';
      ctx.fillText(bLabel, canvas.width - pad, y);
      ctx.textAlign = 'center';
      ctx.fillStyle = '#7dd3fc';
      ctx.fillText(`Mirror · ${angleLabel}`, canvas.width / 2, y);

      const url = await new Promise<string>((resolve, reject) =>
        canvas.toBlob(
          (b) => (b ? resolve(URL.createObjectURL(b)) : reject(new Error('toBlob failed'))),
          'image/jpeg',
          0.92,
        ),
      );
      setExportUrl(url);
    } catch {
      setExportErr(
        'Export failed (the browser may block reading cross-origin images). Try again.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">Export comparison</p>
          <p className="text-[11px] text-mute">
            Saves locally. Nothing leaves your device.
          </p>
        </div>
        <button className="btn-ghost text-xs" onClick={buildExport} disabled={busy}>
          {busy ? 'Rendering…' : 'Generate image'}
        </button>
      </div>
      {exportErr && <p className="text-xs text-red-400">{exportErr}</p>}
      {exportUrl && (
        <div className="space-y-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={exportUrl} alt="Comparison export" className="w-full rounded-xl" />
          <a
            ref={linkRef}
            href={exportUrl}
            download="mirror-comparison.jpg"
            className="btn-primary w-full"
          >
            Download
          </a>
        </div>
      )}
    </div>
  );
}

// Draw an image into a target rect using object-fit: cover semantics.
function drawCover(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  dx: number,
  dy: number,
  dw: number,
  dh: number,
) {
  const ir = img.width / img.height;
  const tr = dw / dh;
  let sx = 0;
  let sy = 0;
  let sw = img.width;
  let sh = img.height;
  if (ir > tr) {
    sw = img.height * tr;
    sx = (img.width - sw) / 2;
  } else {
    sh = img.width / tr;
    sy = (img.height - sh) / 2;
  }
  ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh);
}
