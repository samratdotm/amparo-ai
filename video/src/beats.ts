// Single source of truth for the timeline: scene durations, and the per-beat
// voiceover + caption placement at ABSOLUTE frames so audio, captions, and
// visuals stay locked together.
export const FPS = 30;
export const TRANSITION = 15;

// Visual scenes, in order. Durations in frames (30fps).
export const SCENES = [
  {id: 'hook', dur: 105},
  {id: 'problem', dur: 100},
  {id: 'reveal', dur: 175},
  {id: 'demo', dur: 600},
  {id: 'call', dur: 235},
  {id: 'outro', dur: 155},
] as const;

export type SceneId = (typeof SCENES)[number]['id'];

export const sceneDur = (id: SceneId): number => SCENES.find((s) => s.id === id)!.dur;

// Absolute start frame of a scene, accounting for transition overlap.
export const sceneStart = (id: SceneId): number => {
  const index = SCENES.findIndex((s) => s.id === id);
  return SCENES.slice(0, index).reduce((a, s) => a + s.dur, 0) - index * TRANSITION;
};

export const TOTAL =
  SCENES.reduce((a, s) => a + s.dur, 0) - (SCENES.length - 1) * TRANSITION;

// Beats: one VO clip + caption, placed at an absolute frame. `dur` is the
// measured clip length in frames (used to time the caption out).
export type Beat = {clip: string; at: number; dur: number; caption: string};

const demo = sceneStart('demo');

export const BEATS: Beat[] = [
  {clip: 'vo-1.mp3', at: sceneStart('hook'), dur: 88, caption: 'The cheapest plan is often the priciest.'},
  {clip: 'vo-2.mp3', at: sceneStart('problem'), dur: 82, caption: 'Nobody reads 80 pages of fine print.'},
  {clip: 'vo-3.mp3', at: sceneStart('reveal'), dur: 148, caption: 'Meet Amparo — just ask, out loud.'},
  {clip: 'vo-4.mp3', at: demo + 6, dur: 146, caption: '~40 live lookups · under 100ms'},
  {clip: 'vo-5.mp3', at: demo + 156, dur: 202, caption: 'Cheapest premium = +$22,000 / year'},
  {clip: 'vo-6.mp3', at: demo + 366, dur: 191, caption: 'Every fact cited to the real PDF'},
  {clip: 'vo-7.mp3', at: sceneStart('call') + 18, dur: 102, caption: 'Speaks 40+ languages'},
  {clip: 'vo-8.mp3', at: sceneStart('outro') + 6, dur: 126, caption: 'Coverage clarity, in your language.'},
];
