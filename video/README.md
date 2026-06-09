# Amparo AI — promo video (Remotion)

A code-based promo video for GitHub / LinkedIn, built with [Remotion](https://remotion.dev).
Sliding scene transitions, animated feature reveals, stat counters, and an animated
re-creation of the live coverage-comparison panel.

## Run

```bash
cd video
npm install
npm start          # opens Remotion Studio — live preview + scrubbing at localhost:3000
```

## Render the MP4

```bash
npm run build              # → out/amparo-promo.mp4   (1920×1080, ~55s)
npm run build:linkedin     # → out/amparo-promo-square.mp4  (1080×1080 for the LinkedIn feed)
```

## Customize

| Want to change… | Edit |
|---|---|
| Scene order / transitions | `src/AmparoPromo.tsx` |
| Scene lengths (total auto-recalculates) | `src/timing.ts` |
| Colors / fonts | `src/theme.ts` |
| Headline & tagline | `src/scenes/TitleScene.tsx`, `OutroScene.tsx` |
| Feature bullets | `src/scenes/FeaturesScene.tsx` |
| Stat numbers | `src/scenes/StatsScene.tsx` |
| Your real screen recording | put `public/demo.mp4`, set `HAS_RECORDING = true` in `src/scenes/DemoScene.tsx` |

## Structure

```
src/
  index.ts            registerRoot
  Root.tsx            Composition (1920×1080, 30fps)
  AmparoPromo.tsx     scene sequence + slide transitions
  timing.ts           durations (single source of truth)
  theme.ts            palette + font stack
  components/         SlideIn, Counter, Background
  scenes/            Title · Problem · Features · Stats · Demo · Outro
```

> Tip: if `npm install` warns about mismatched Remotion package versions, run
> `npm run upgrade` to align them all to the latest 4.x.
