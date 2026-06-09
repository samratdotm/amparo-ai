import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Background} from '../components/Background';
import {GradientText} from '../components/GradientText';
import {SlideIn} from '../components/SlideIn';
import {FONT, theme} from '../theme';

const STACK = ['LiveKit', 'Moss', 'MiniMax', 'Unsiloed'];

export const OutroScene: React.FC = () => {
  return (
    <Background glow={theme.green}>
      <AbsoluteFill
        style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT}}
      >
        <SlideIn direction="up" delay={4}>
          <div style={{color: theme.text, fontSize: 126, fontWeight: 800}}>
            Amparo
            <GradientText colors={[theme.green, '#5EEAD4']}> AI</GradientText>
          </div>
        </SlideIn>
        <SlideIn direction="up" delay={14}>
          <div style={{color: theme.textMuted, fontSize: 38, fontWeight: 500, marginTop: 8}}>
            Coverage clarity, in your language — every fact cited.
          </div>
        </SlideIn>
        <SlideIn direction="up" delay={24}>
          <div style={{display: 'flex', gap: 16, marginTop: 44}}>
            {STACK.map((s) => (
              <div
                key={s}
                style={{
                  color: theme.text,
                  fontSize: 26,
                  fontWeight: 600,
                  padding: '12px 24px',
                  borderRadius: 30,
                  background: theme.bgElevated,
                  border: `1px solid ${theme.border}`,
                }}
              >
                {s}
              </div>
            ))}
          </div>
        </SlideIn>
        <SlideIn direction="up" delay={38}>
          <div style={{marginTop: 60, color: theme.green, fontSize: 40, fontWeight: 700}}>
            github.com/samratdotm · @samratdotm
          </div>
        </SlideIn>
      </AbsoluteFill>
    </Background>
  );
};
