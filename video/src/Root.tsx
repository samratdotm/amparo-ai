import React from 'react';
import {Composition} from 'remotion';
import {AmparoPromo} from './AmparoPromo';
import {PanelLoop} from './PanelLoop';
import {FPS, TOTAL} from './beats';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="AmparoPromo"
        component={AmparoPromo}
        durationInFrames={TOTAL}
        fps={FPS}
        width={1920}
        height={1080}
      />
      {/* Looping panel build, rendered to an autoplaying GIF for the README. */}
      <Composition
        id="PanelLoop"
        component={PanelLoop}
        durationInFrames={240}
        fps={FPS}
        width={1280}
        height={720}
      />
    </>
  );
};
