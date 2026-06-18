import type { HistoParameters, HistoTimeBySize } from '../../../types/simulation';

export type BiopsySize = 'small' | 'medium' | 'large';

export function getTimeBySize(
  block: HistoTimeBySize,
  size: BiopsySize,
  fallback: number,
): number {
  return block.by_size[size]?.params[0] ?? fallback;
}

export function patchTimeBySize(
  block: HistoTimeBySize,
  size: BiopsySize,
  value: number,
): HistoTimeBySize {
  return {
    by_size: {
      ...block.by_size,
      [size]: {
        ...block.by_size[size],
        distribution: 'constant',
        params: [value],
      },
    },
  };
}

export function patchHistoStation<K extends keyof HistoParameters>(
  parameters: HistoParameters,
  key: K,
  patch: Partial<HistoParameters[K]>,
): HistoParameters {
  return {
    ...parameters,
    [key]: { ...(parameters[key] as object), ...patch },
  };
}
