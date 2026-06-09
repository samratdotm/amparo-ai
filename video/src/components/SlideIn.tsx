import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

type Direction = 'left' | 'right' | 'up' | 'down';

/**
 * Springs a child into place from the given direction with a gentle overshoot,
 * a slight scale pop, and a fade. `delay` is in frames.
 */
export const SlideIn: React.FC<{
  children: React.ReactNode;
  delay?: number;
  direction?: Direction;
  distance?: number;
  style?: React.CSSProperties;
}> = ({children, delay = 0, direction = 'left', distance = 80, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Lower damping => a small, tasteful overshoot at the end of the slide.
  const progress = spring({
    frame: frame - delay,
    fps,
    config: {damping: 15, mass: 0.85, stiffness: 110},
  });

  const offset = interpolate(progress, [0, 1], [distance, 0]);
  const opacity = interpolate(progress, [0, 1], [0, 1], {extrapolateRight: 'clamp'});
  const scale = interpolate(progress, [0, 1], [0.96, 1]);

  const axis = direction === 'left' || direction === 'right' ? 'X' : 'Y';
  const sign = direction === 'left' || direction === 'up' ? -1 : 1;

  return (
    <div
      style={{
        ...style,
        opacity,
        transform: `translate${axis}(${offset * sign}px) scale(${scale})`,
      }}
    >
      {children}
    </div>
  );
};
