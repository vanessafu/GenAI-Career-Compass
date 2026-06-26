export type LoadingProgressMilestone = {
  elapsedMs: number;
  step: number;
  progress: number;
};

export type LoadingProgressConfig = readonly LoadingProgressMilestone[];

export const CV_UPLOAD_PROGRESS = [
  { elapsedMs: 0, step: 0, progress: 8 },
  { elapsedMs: 3500, step: 0, progress: 26 },
  { elapsedMs: 8000, step: 1, progress: 52 },
  { elapsedMs: 16000, step: 2, progress: 78 },
  { elapsedMs: 30000, step: 2, progress: 88 },
] as const satisfies LoadingProgressConfig;

export const MANUAL_PROFILE_PROGRESS = [
  { elapsedMs: 0, step: 0, progress: 8 },
  { elapsedMs: 2500, step: 0, progress: 28 },
  { elapsedMs: 6000, step: 1, progress: 56 },
  { elapsedMs: 12000, step: 2, progress: 82 },
  { elapsedMs: 20000, step: 2, progress: 88 },
] as const satisfies LoadingProgressConfig;

export const MATCHING_PROGRESS = [
  { elapsedMs: 0, step: 0, progress: 8 },
  { elapsedMs: 3000, step: 0, progress: 28 },
  { elapsedMs: 7000, step: 1, progress: 56 },
  { elapsedMs: 14000, step: 2, progress: 80 },
  { elapsedMs: 24000, step: 2, progress: 89 },
] as const satisfies LoadingProgressConfig;

export const PATH_PREP_PROGRESS = [
  { elapsedMs: 0, step: 0, progress: 8 },
  { elapsedMs: 2500, step: 0, progress: 30 },
  { elapsedMs: 6500, step: 1, progress: 58 },
  { elapsedMs: 12000, step: 2, progress: 82 },
  { elapsedMs: 22000, step: 2, progress: 89 },
] as const satisfies LoadingProgressConfig;

function clampProgress(value: number): number {
  return Math.max(0, Math.min(95, value));
}

export function getLoadingProgressState(config: LoadingProgressConfig, elapsedMs: number) {
  if (config.length === 0) return { step: 0, progress: 0 };

  const safeElapsed = Math.max(0, elapsedMs);
  let current = config[0];
  let next: LoadingProgressMilestone | null = null;

  for (const milestone of config) {
    if (milestone.elapsedMs <= safeElapsed) {
      current = milestone;
      next = null;
    } else {
      next = milestone;
      break;
    }
  }

  if (!next) {
    return {
      step: current.step,
      progress: clampProgress(current.progress),
    };
  }

  const span = next.elapsedMs - current.elapsedMs;
  const ratio = span > 0 ? (safeElapsed - current.elapsedMs) / span : 1;
  const progress = current.progress + (next.progress - current.progress) * ratio;

  return {
    step: current.step,
    progress: clampProgress(progress),
  };
}
