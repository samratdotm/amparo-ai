import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Panel} from './components/Panel';
import {FONT, theme} from './theme';

/**
 * Standalone, GIF-optimized loop of the panel building (counters → trap →
 * citations). No film grain / drifting aurora — a static background compresses
 * cleanly to GIF. Rendered for the autoplaying README hero.
 */
export const PanelLoop: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: theme.bg, fontFamily: FONT, justifyContent: 'center', alignItems: 'center', padding: 56}}>
      <AbsoluteFill style={{background: `radial-gradient(1000px 540px at 50% 0%, ${theme.green}22, transparent 60%)`}} />
      <div style={{width: '100%'}}>
        <Panel countersDelay={6} trapDelay={70} plansDelay={80} citeDelay={150} />
      </div>
    </AbsoluteFill>
  );
};
