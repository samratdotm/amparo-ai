import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile} from 'remotion';
import {Background} from '../components/Background';
import {Counter} from '../components/Counter';
import {SlideIn} from '../components/SlideIn';
import {FONT, MONO, theme} from '../theme';

// ── Drop in your real screen recording ──────────────────────────────────────
// Record the live panel at localhost:3000 while calling the agent from your
// phone, save it as  video/public/demo.mp4 , then flip this to true.
const HAS_RECORDING = false;

const StatBox: React.FC<{label: string; value: React.ReactNode; color: string}> = ({label, value, color}) => (
  <div style={{flex: 1, padding: '22px 26px', borderRadius: 16, background: theme.bg, border: `1px solid ${theme.border}`}}>
    <div style={{color: theme.textMuted, fontSize: 20, fontWeight: 600, letterSpacing: 1}}>{label}</div>
    <div style={{color, fontSize: 56, fontWeight: 800, marginTop: 6}}>{value}</div>
  </div>
);

const PLANS = [
  {rank: '#1', name: 'Blue Shield HDHP PPO', cost: '$17,675/yr', trap: false, cite: 'Blue Shield SBC 2024'},
  {rank: '#2', name: 'Kaiser Gold HMO', cost: '$41,705/yr', trap: true, cite: 'Kaiser SBC 2024'},
  {rank: '#3', name: 'CCHP Bronze HMO', cost: '$61,877/yr', trap: true, cite: 'CCHP SBC 2024'},
];

/**
 * Animated re-creation of the live PlanComparisonPanel, revealed progressively
 * across the scene to match the three demo voiceover beats:
 *   ~6   counters spin up        ("~40 live lookups")
 *   ~150 trap banner + plans     ("+$22,000 / year")
 *   ~360 citation chips light up ("every fact cited")
 */
const MockPanel: React.FC = () => (
  <div style={{padding: 40}}>
    <div style={{display: 'flex', gap: 24, marginBottom: 28}}>
      <StatBox label="MOSS LOOKUPS" color={theme.green} value={<Counter to={28} delay={8} duration={70} />} />
      <StatBox label="TOTAL THIS SESSION" color={theme.blue} value={<Counter to={52} delay={12} duration={80} />} />
      <StatBox label="PLANS COMPARED" color={theme.purple} value={<Counter to={4} delay={16} duration={40} />} />
    </div>

    <SlideIn direction="left" delay={150}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          padding: '18px 22px',
          borderRadius: 14,
          background: `${theme.red}14`,
          border: `1px solid ${theme.red}55`,
          marginBottom: 24,
        }}
      >
        <div style={{color: theme.red, fontSize: 30}}>⚠</div>
        <div style={{color: theme.red, fontSize: 25, fontWeight: 600}}>
          Cheap-plan trap — CCHP's low premium hides $25k+ out-of-network costs not capped by the OOP max.
        </div>
      </div>
    </SlideIn>

    {PLANS.map((p, i) => (
      <SlideIn key={p.name} direction="right" delay={162 + i * 16} distance={160}>
        <div
          style={{
            padding: '22px 28px',
            borderRadius: 14,
            background: theme.bg,
            border: `1px solid ${p.trap ? theme.red + '66' : theme.border}`,
            marginBottom: 14,
          }}
        >
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 18}}>
              <span style={{color: theme.textMuted, fontSize: 26, fontWeight: 700}}>{p.rank}</span>
              <span style={{color: theme.text, fontSize: 30, fontWeight: 700}}>{p.name}</span>
              {p.trap && (
                <span style={{color: theme.red, fontSize: 20, fontWeight: 700, border: `1px solid ${theme.red}`, borderRadius: 20, padding: '4px 14px'}}>
                  ⚠ TRAP
                </span>
              )}
            </div>
            <span style={{color: p.trap ? theme.red : theme.green, fontSize: 34, fontWeight: 800, fontFamily: MONO}}>
              {p.cost}
            </span>
          </div>
          {/* Citation chip lights up on the third beat. */}
          <SlideIn direction="up" delay={366 + i * 12} distance={40}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                marginTop: 14,
                padding: '8px 16px',
                borderRadius: 20,
                background: `${theme.blue}1A`,
                border: `1px solid ${theme.blue}55`,
                color: theme.blue,
                fontSize: 20,
                fontWeight: 600,
              }}
            >
              📄 {p.cite} ↗
            </div>
          </SlideIn>
        </div>
      </SlideIn>
    ))}
  </div>
);

export const DemoScene: React.FC = () => {
  return (
    <Background glow={theme.green}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT, padding: 80}}>
        <SlideIn direction="up" delay={2} style={{width: '100%'}}>
          <div
            style={{
              borderRadius: 20,
              overflow: 'hidden',
              border: `1px solid ${theme.border}`,
              background: theme.bgElevated,
              boxShadow: '0 40px 120px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{display: 'flex', alignItems: 'center', gap: 10, padding: '16px 22px', background: '#101216', borderBottom: `1px solid ${theme.border}`}}>
              <div style={{width: 14, height: 14, borderRadius: 7, background: '#FF5F57'}} />
              <div style={{width: 14, height: 14, borderRadius: 7, background: '#FEBC2E'}} />
              <div style={{width: 14, height: 14, borderRadius: 7, background: '#28C840'}} />
              <div style={{marginLeft: 18, color: theme.textMuted, fontSize: 22}}>amparo-ai · live coverage comparison</div>
            </div>
            {HAS_RECORDING ? (
              <OffthreadVideo src={staticFile('demo.mp4')} style={{width: '100%', display: 'block'}} />
            ) : (
              <MockPanel />
            )}
          </div>
        </SlideIn>
      </AbsoluteFill>
    </Background>
  );
};
