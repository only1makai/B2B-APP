'use client';

import { useEffect } from 'react';

// Registers the service worker so Mirror is installable as a PWA.
export function ServiceWorker() {
  useEffect(() => {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
    if (process.env.NODE_ENV !== 'production') return;
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Registration failure is non-fatal; the app still works online.
    });
  }, []);
  return null;
}
