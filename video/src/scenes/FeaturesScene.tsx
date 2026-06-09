import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Background} from '../components/Background';
import {SlideIn} from '../components/SlideIn';
import {FONT, theme} from '../theme';

const FEATURES = [
  {
    icon: '🎙️',
    title: 'Speak naturally — in any language',
    sub: 'Live voice via LiveKit · 40+ languages, auto code-switching',
    color: theme.green,
  },
  {
    icon: '⚡',
    title: '~40 Moss retrievals in <100ms',
    sub: 'Fact-level lookups fired concurrently every single turn',
    color: theme.blue,
  },
  {
    icon: '🧮',
    title: 'Real costs, computed — never guessed',
    sub: 'Deterministic math exposes the cheap-plan trap',
    color: theme.amber,
  },
  {
    icon: '📄',
    title: 'Every answer cited to the source',
    sub: 'Bbox citations into the real plan PDFs, powered by Unsiloed',
    color: theme.purple,
  },
];

export const FeaturesScene: React.FC = () => {
  return (
    <Background glow={theme.blue}>
      <AbsoluteFill
        style={{justifyContent: 'center', paddingLeft: 160, paddingRight: 160, fontFamily: FONT}}
      >
        <SlideIn direction="up" delay={2}>
          <div style={{color: theme.text, fontSize: 58, fontWeight: 800, marginBottom: 44}}>
            One messy question → a cited answer.
          </div>
        </SlideIn>
        {FEATURES.map((f, i) => (
          <SlideIn key={f.title} direction="left" delay={22 + i * 24} distance={140}>
            <div style={{display: 'flex', alignItems: 'center', gap: 28, padding: '20px 0'}}>
              <div
                style={{
                  fontSize: 52,
                  width: 88,
                  height: 88,
                  borderRadius: 18,
                  background: `${f.color}1A`,
                  border: `1px solid ${f.color}44`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                {f.icon}
              </div>
              <div>
                <div style={{color: theme.text, fontSize: 44, fontWeight: 700}}>{f.title}</div>
                <div style={{color: theme.textMuted, fontSize: 29, fontWeight: 500, marginTop: 4}}>
                  {f.sub}
                </div>
              </div>
            </div>
          </SlideIn>
        ))}
      </AbsoluteFill>
    </Background>
  );
};
