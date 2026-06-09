import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Background} from '../components/Background';
import {Counter} from '../components/Counter';
import {SlideIn} from '../components/SlideIn';
import {FONT, theme} from '../theme';

const STATS = [
  {to: 40, suffix: '+', label: 'Moss lookups / turn', color: theme.green, decimals: 0},
  {to: 100, prefix: '<', suffix: 'ms', label: 'retrieval latency', color: theme.blue, decimals: 0},
  {to: 4, label: 'plans compared in parallel', color: theme.purple, decimals: 0},
  {to: 40, suffix: '+', label: 'languages spoken', color: theme.amber, decimals: 0},
];

export const StatsScene: React.FC = () => {
  return (
    <Background glow={theme.purple}>
      <AbsoluteFill
        style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT}}
      >
        <SlideIn direction="up" delay={2}>
          <div style={{color: theme.text, fontSize: 58, fontWeight: 800, marginBottom: 64}}>
            Built to make Moss the hero.
          </div>
        </SlideIn>
        <div style={{display: 'flex', gap: 36}}>
          {STATS.map((s, i) => (
            <SlideIn key={s.label} direction="up" delay={16 + i * 10} distance={90}>
              <div
                style={{
                  width: 360,
                  padding: '40px 30px',
                  borderRadius: 24,
                  background: theme.bgElevated,
                  border: `1px solid ${theme.border}`,
                  textAlign: 'center',
                }}
              >
                <div style={{color: s.color, fontSize: 92, fontWeight: 800}}>
                  <Counter
                    to={s.to}
                    delay={16 + i * 10 + 6}
                    prefix={s.prefix}
                    suffix={s.suffix}
                    decimals={s.decimals}
                  />
                </div>
                <div style={{color: theme.textMuted, fontSize: 26, fontWeight: 500, marginTop: 8}}>
                  {s.label}
                </div>
              </div>
            </SlideIn>
          ))}
        </div>
      </AbsoluteFill>
    </Background>
  );
};
