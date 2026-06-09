import React from 'react';
import {Counter} from './Counter';
import {SlideIn} from './SlideIn';
import {MONO, theme} from '../theme';

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
 * The live-panel re-creation (browser chrome + Moss counters + trap + ranked
 * plans + citation chips), revealed progressively. Delays are parameterized so
 * the full promo (DemoScene) and the looping GIF (PanelLoop) can pace it
 * differently from the same source.
 */
export const Panel: React.FC<{
  countersDelay?: number;
  trapDelay?: number;
  plansDelay?: number;
  citeDelay?: number;
}> = ({countersDelay = 8, trapDelay = 150, plansDelay = 162, citeDelay = 366}) => (
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
    <div style={{padding: 40}}>
      <div style={{display: 'flex', gap: 24, marginBottom: 28}}>
        <StatBox label="MOSS LOOKUPS" color={theme.green} value={<Counter to={28} delay={countersDelay} duration={70} />} />
        <StatBox label="TOTAL THIS SESSION" color={theme.blue} value={<Counter to={52} delay={countersDelay + 4} duration={80} />} />
        <StatBox label="PLANS COMPARED" color={theme.purple} value={<Counter to={4} delay={countersDelay + 8} duration={40} />} />
      </div>

      <SlideIn direction="left" delay={trapDelay}>
        <div style={{display: 'flex', alignItems: 'center', gap: 14, padding: '18px 22px', borderRadius: 14, background: `${theme.red}14`, border: `1px solid ${theme.red}55`, marginBottom: 24}}>
          <div style={{color: theme.red, fontSize: 30}}>⚠</div>
          <div style={{color: theme.red, fontSize: 25, fontWeight: 600}}>
            Cheap-plan trap — CCHP's low premium hides $25k+ out-of-network costs not capped by the OOP max.
          </div>
        </div>
      </SlideIn>

      {PLANS.map((p, i) => (
        <SlideIn key={p.name} direction="right" delay={plansDelay + i * 16} distance={160}>
          <div style={{padding: '22px 28px', borderRadius: 14, background: theme.bg, border: `1px solid ${p.trap ? theme.red + '66' : theme.border}`, marginBottom: 14}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <div style={{display: 'flex', alignItems: 'center', gap: 18}}>
                <span style={{color: theme.textMuted, fontSize: 26, fontWeight: 700}}>{p.rank}</span>
                <span style={{color: theme.text, fontSize: 30, fontWeight: 700}}>{p.name}</span>
                {p.trap && (
                  <span style={{color: theme.red, fontSize: 20, fontWeight: 700, border: `1px solid ${theme.red}`, borderRadius: 20, padding: '4px 14px'}}>⚠ TRAP</span>
                )}
              </div>
              <span style={{color: p.trap ? theme.red : theme.green, fontSize: 34, fontWeight: 800, fontFamily: MONO}}>{p.cost}</span>
            </div>
            <SlideIn direction="up" delay={citeDelay + i * 12} distance={40}>
              <div style={{display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 14, padding: '8px 16px', borderRadius: 20, background: `${theme.blue}1A`, border: `1px solid ${theme.blue}55`, color: theme.blue, fontSize: 20, fontWeight: 600}}>
                📄 {p.cite} ↗
              </div>
            </SlideIn>
          </div>
        </SlideIn>
      ))}
    </div>
  </div>
);
