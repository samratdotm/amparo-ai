import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Background} from '../components/Background';
import {SlideIn} from '../components/SlideIn';
import {FONT, theme} from '../theme';

/** Cold-open hook — the pain, stated in the first seconds. */
export const HookScene: React.FC = () => {
  return (
    <Background glow={theme.red}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT, padding: 140}}>
        <SlideIn direction="up" delay={2}>
          <div style={{color: theme.textMuted, fontSize: 36, fontWeight: 600, letterSpacing: 2, marginBottom: 18}}>
            Your cheapest health plan?
          </div>
        </SlideIn>
        <SlideIn direction="up" delay={10}>
          <div style={{color: theme.text, fontSize: 130, fontWeight: 800, textAlign: 'center', lineHeight: 1.02}}>
            It's often a <span style={{color: theme.red}}>trap.</span>
          </div>
        </SlideIn>
      </AbsoluteFill>
    </Background>
  );
};
