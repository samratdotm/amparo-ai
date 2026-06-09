import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {theme} from '../theme';

const GRAIN_SVG = `<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(#n)'/></svg>`;
const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(GRAIN_SVG)}")`;

/**
 * Dark base with two slowly drifting aurora blobs, a faded tech grid, a subtle
 * Ken Burns push-in on the content, and a film-grain + vignette grade on top.
 */
export const Background: React.FC<{
  glow?: string;
  zoom?: boolean;
  children?: React.ReactNode;
}> = ({glow = theme.green, zoom = true, children}) => {
  const frame = useCurrentFrame();

  // Drifting aurora positions (percent of frame).
  const ax = 50 + Math.sin(frame * 0.012) * 9;
  const ay = -12 + Math.cos(frame * 0.01) * 6;
  const bx = 28 + Math.cos(frame * 0.009) * 10;
  const by = 24 + Math.sin(frame * 0.013) * 7;

  // Ken Burns push-in that settles after ~8s.
  const scale = zoom ? interpolate(frame, [0, 240], [1.0, 1.04], {extrapolateRight: 'clamp'}) : 1;
  const ty = zoom ? interpolate(frame, [0, 240], [0, -10], {extrapolateRight: 'clamp'}) : 0;

  // Crawling film grain — shift the noise tile each frame.
  const gx = (frame * 7) % 220;
  const gy = (frame * 13) % 220;

  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{background: `radial-gradient(900px 520px at ${ax}% ${ay}%, ${glow}2E, transparent 60%)`}}
      />
      <AbsoluteFill
        style={{background: `radial-gradient(760px 480px at ${bx}% ${by}%, ${theme.blue}1F, transparent 62%)`}}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${theme.border}55 1px, transparent 1px), linear-gradient(90deg, ${theme.border}55 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
          maskImage: 'radial-gradient(ellipse at center, black 35%, transparent 78%)',
          WebkitMaskImage: 'radial-gradient(ellipse at center, black 35%, transparent 78%)',
        }}
      />
      <AbsoluteFill style={{transform: `scale(${scale}) translateY(${ty}px)`}}>{children}</AbsoluteFill>
      <AbsoluteFill
        style={{
          backgroundImage: GRAIN,
          backgroundPosition: `${gx}px ${gy}px`,
          opacity: 0.05,
          mixBlendMode: 'overlay',
          pointerEvents: 'none',
        }}
      />
      <AbsoluteFill
        style={{
          background: 'radial-gradient(ellipse at center, transparent 52%, rgba(0,0,0,0.55) 100%)',
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
