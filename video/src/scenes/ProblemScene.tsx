import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Background} from '../components/Background';
import {SlideIn} from '../components/SlideIn';
import {FONT, theme} from '../theme';

/** Problem amplification — tight, one idea. */
export const ProblemScene: React.FC = () => {
  return (
    <Background glow={theme.amber}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT, padding: 140}}>
        <SlideIn direction="left" delay={2}>
          <div style={{color: theme.text, fontSize: 88, fontWeight: 800, textAlign: 'center', lineHeight: 1.08}}>
            Nobody reads
            <br />
            <span style={{color: theme.amber}}>80 pages</span> of fine print.
          </div>
        </SlideIn>
        <SlideIn direction="up" delay={16}>
          <div style={{color: theme.textMuted, fontSize: 34, fontWeight: 500, marginTop: 28}}>
            So the real costs stay hidden — until the bill.
          </div>
        </SlideIn>
      </AbsoluteFill>
    </Background>
  );
};
