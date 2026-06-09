import React from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';

/** Eases a number from 0 → `to`, with optional prefix/suffix and decimals. */
export const Counter: React.FC<{
  to: number;
  delay?: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  style?: React.CSSProperties;
}> = ({to, delay = 0, duration = 40, prefix = '', suffix = '', decimals = 0, style}) => {
  const frame = useCurrentFrame();
  const value = interpolate(frame - delay, [0, duration], [0, to], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  return (
    <span style={style}>
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
};
