import React from 'react';
import {useCurrentFrame} from 'remotion';

/** Text filled with an animated gradient sheen that sweeps across it. */
export const GradientText: React.FC<{
  children: React.ReactNode;
  colors: [string, string];
  style?: React.CSSProperties;
}> = ({children, colors, style}) => {
  const frame = useCurrentFrame();
  const pos = (frame * 1.6) % 200;
  return (
    <span
      style={{
        ...style,
        backgroundImage: `linear-gradient(100deg, ${colors[0]}, ${colors[1]}, ${colors[0]})`,
        backgroundSize: '200% 100%',
        backgroundPosition: `${pos}% 0`,
        WebkitBackgroundClip: 'text',
        backgroundClip: 'text',
        color: 'transparent',
        WebkitTextFillColor: 'transparent',
      }}
    >
      {children}
    </span>
  );
};
