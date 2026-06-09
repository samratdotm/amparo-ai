import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {BEATS} from '../beats';
import {FONT, theme} from '../theme';

/**
 * Lower-third caption overlay. Renders the beat active at the current frame,
 * fading in/out. Synced to the same absolute frames as the VO clips, so the
 * words on screen match the words being spoken (and read fine when muted).
 */
export const Captions: React.FC = () => {
  const frame = useCurrentFrame();

  const active = BEATS.find((b) => frame >= b.at && frame <= b.at + b.dur + 12);
  if (!active) return null;

  const start = active.at;
  const end = active.at + active.dur + 12;
  const opacity =
    interpolate(frame, [start, start + 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) *
    interpolate(frame, [end - 9, end], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const rise = interpolate(frame, [start, start + 10], [14, 0], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 90, fontFamily: FONT}}>
      <div
        style={{
          opacity,
          transform: `translateY(${rise}px)`,
          maxWidth: 1200,
          textAlign: 'center',
          padding: '18px 34px',
          borderRadius: 16,
          background: 'rgba(10,11,13,0.72)',
          border: `1px solid ${theme.border}`,
          backdropFilter: 'blur(8px)',
          color: theme.text,
          fontSize: 40,
          fontWeight: 600,
          lineHeight: 1.25,
        }}
      >
        {active.caption}
      </div>
    </AbsoluteFill>
  );
};
