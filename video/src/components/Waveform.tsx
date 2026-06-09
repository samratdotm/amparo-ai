import React from 'react';
import {useCurrentFrame} from 'remotion';

/** A live-looking audio waveform: rounded bars, taller in the centre, animated. */
export const Waveform: React.FC<{
  bars?: number;
  color: string;
  width?: number;
  height?: number;
  speed?: number;
}> = ({bars = 40, color, width = 600, height = 70, speed = 0.2}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, width, height}}>
      {Array.from({length: bars}).map((_, i) => {
        const env = 0.35 + 0.65 * Math.sin((i / (bars - 1)) * Math.PI); // centre taper
        const a = 0.5 + 0.5 * Math.sin(frame * speed + i * 0.55);
        const h = Math.max(6, 6 + a * (height - 6) * env);
        return (
          <div
            key={i}
            style={{
              width: 6,
              height: h,
              borderRadius: 3,
              background: color,
              opacity: 0.55 + 0.45 * env,
            }}
          />
        );
      })}
    </div>
  );
};
