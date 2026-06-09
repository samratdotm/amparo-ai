import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Background} from '../components/Background';
import {GradientText} from '../components/GradientText';
import {SlideIn} from '../components/SlideIn';
import {Waveform} from '../components/Waveform';
import {FONT, theme} from '../theme';

export const TitleScene: React.FC = () => {
  return (
    <Background glow={theme.green}>
      <AbsoluteFill
        style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT}}
      >
        <SlideIn direction="up" delay={4}>
          <div
            style={{
              color: theme.green,
              fontSize: 26,
              fontWeight: 600,
              letterSpacing: 6,
              textTransform: 'uppercase',
              marginBottom: 24,
            }}
          >
            Moss @ YC Hackathon
          </div>
        </SlideIn>
        <SlideIn direction="left" delay={10}>
          <div style={{color: theme.text, fontSize: 168, fontWeight: 800, letterSpacing: -4}}>
            Amparo
            <GradientText colors={[theme.green, '#5EEAD4']}> AI</GradientText>
          </div>
        </SlideIn>
        <SlideIn direction="right" delay={22}>
          <div style={{color: theme.textMuted, fontSize: 46, fontWeight: 500, marginTop: 16}}>
            Insurance you can finally understand.
          </div>
        </SlideIn>
        <SlideIn direction="up" delay={34}>
          <div style={{marginTop: 44}}>
            <Waveform bars={48} color={theme.green} width={680} height={60} speed={0.22} />
          </div>
        </SlideIn>
      </AbsoluteFill>
    </Background>
  );
};
