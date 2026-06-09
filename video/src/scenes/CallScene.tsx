import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Background} from '../components/Background';
import {SlideIn} from '../components/SlideIn';
import {Waveform} from '../components/Waveform';
import {FONT, theme} from '../theme';

const Bubble: React.FC<{
  side: 'left' | 'right';
  accent: string;
  children: React.ReactNode;
}> = ({side, accent, children}) => (
  <div
    style={{
      maxWidth: 860,
      marginLeft: side === 'right' ? 'auto' : 0,
      marginRight: side === 'left' ? 'auto' : 0,
      padding: '24px 30px',
      borderRadius: 22,
      borderBottomRightRadius: side === 'right' ? 6 : 22,
      borderBottomLeftRadius: side === 'left' ? 6 : 22,
      background: side === 'right' ? `${accent}1A` : theme.bgElevated,
      border: `1px solid ${side === 'right' ? accent + '55' : theme.border}`,
      color: theme.text,
      fontSize: 34,
      fontWeight: 500,
      lineHeight: 1.32,
    }}
  >
    {children}
  </div>
);

export const CallScene: React.FC = () => {
  return (
    <Background glow={theme.blue}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT, padding: 120}}>
        <div style={{width: 1320, maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: 22}}>
          <SlideIn direction="up" delay={2}>
            <div style={{display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14}}>
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: 7,
                  background: theme.green,
                  boxShadow: `0 0 16px ${theme.green}`,
                }}
              />
              <div style={{color: theme.textMuted, fontSize: 26, fontWeight: 600}}>Live call · Amparo</div>
              <Waveform bars={26} color={theme.green} width={240} height={36} speed={0.3} />
            </div>
          </SlideIn>

          <SlideIn direction="right" delay={14} distance={180}>
            <Bubble side="right" accent={theme.blue}>
              “Tomo Humira y mi doctora está en UCSF — ¿cuál plan me conviene?”
            </Bubble>
          </SlideIn>

          <SlideIn direction="left" delay={42}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 12,
                alignSelf: 'flex-start',
                padding: '12px 20px',
                borderRadius: 30,
                background: theme.bg,
                border: `1px solid ${theme.border}`,
                color: theme.textMuted,
                fontSize: 24,
                fontWeight: 600,
              }}
            >
              <span style={{color: theme.amber}}>⚡</span> 24 Moss lookups · 88ms ·{' '}
              <span style={{color: theme.red, fontWeight: 700}}>trap detected</span>
            </div>
          </SlideIn>

          <SlideIn direction="left" delay={62} distance={180}>
            <Bubble side="left" accent={theme.green}>
              “El plan más barato por mes <b style={{color: theme.red}}>en realidad cuesta $22,000 más al
              año</b> — UCSF está fuera de su red, y eso no tiene tope.”
            </Bubble>
          </SlideIn>

          <SlideIn direction="up" delay={92}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                marginTop: 12,
                color: theme.textMuted,
                fontSize: 26,
                fontWeight: 600,
              }}
            >
              <span style={{fontSize: 30}}>🌐</span> Español · English · हिन्दी · 中文 ·{' '}
              <span style={{color: theme.blue}}>+40 languages</span>
            </div>
          </SlideIn>
        </div>
      </AbsoluteFill>
    </Background>
  );
};
