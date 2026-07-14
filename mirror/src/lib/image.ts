// Client-side image utilities for the capture flow.

// Mean perceptual luminance (0-255) of a canvas frame. Sampled (every Nth
// pixel) for speed — we only need a coarse lighting fingerprint, not accuracy.
export function meanLuminance(ctx: CanvasRenderingContext2D, w: number, h: number): number {
  const { data } = ctx.getImageData(0, 0, w, h);
  let sum = 0;
  let n = 0;
  // Step by 40 bytes = every 10th pixel. Plenty for a global average.
  for (let i = 0; i < data.length; i += 40) {
    // Rec. 601 luma.
    sum += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    n++;
  }
  return n ? sum / n : 0;
}

// Draw a video frame to an offscreen canvas and return { blob, width, height,
// luminance }. Mirrors nothing — we keep the raw orientation.
export async function captureFrame(
  video: HTMLVideoElement,
): Promise<{ blob: Blob; width: number; height: number; luminance: number }> {
  const width = video.videoWidth;
  const height = video.videoHeight;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;
  ctx.drawImage(video, 0, 0, width, height);
  const luminance = meanLuminance(ctx, width, height);
  const blob = await new Promise<Blob>((resolve, reject) =>
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error('toBlob failed'))),
      'image/jpeg',
      0.9,
    ),
  );
  return { blob, width, height, luminance };
}
