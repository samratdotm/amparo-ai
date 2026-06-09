import React from 'react';
import {Composition} from 'remotion';
import {AmparoPromo} from './AmparoPromo';
import {FPS, TOTAL} from './beats';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="AmparoPromo"
      component={AmparoPromo}
      durationInFrames={TOTAL}
      fps={FPS}
      width={1920}
      height={1080}
    />
  );
};
