// The pre-capture checklist. Enforced in the UI: you can't shoot until every
// item is confirmed. These are the variables that actually wreck comparability.
export const CAPTURE_CHECKLIST = [
  { id: 'light', label: 'Natural light (near a window, not overhead)' },
  { id: 'flash', label: 'No flash' },
  { id: 'distance', label: "Arm's length from the camera" },
  { id: 'expression', label: 'Neutral expression' },
  { id: 'shower', label: 'Post-shower, clean face' },
] as const;

// Above this mean-luminance delta vs. the last session, warn about lighting
// drift. 0-255 scale; ~28 is a noticeable but not extreme shift.
export const LIGHTING_DELTA_THRESHOLD = 28;
