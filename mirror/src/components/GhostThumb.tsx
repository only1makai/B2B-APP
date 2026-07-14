'use client';

// A plain <img> for a signed photo URL. We use <img> rather than next/image
// because signed URLs are short-lived and per-request — the image optimizer
// would cache them, which is exactly what we don't want for face photos.
export function GhostThumb({
  src,
  className,
  alt = '',
}: {
  src?: string;
  className?: string;
  alt?: string;
}) {
  if (!src) {
    return (
      <div
        className={`flex items-center justify-center bg-ink text-[10px] text-mute ${className ?? ''}`}
      >
        …
      </div>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={className} loading="lazy" />;
}
