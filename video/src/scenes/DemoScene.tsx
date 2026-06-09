import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile} from 'remotion';
import {Background} from '../components/Background';
import {Panel} from '../components/Panel';
import {SlideIn} from '../components/SlideIn';
import {FONT, theme} from '../theme';

// ── Drop in your real screen recording ──────────────────────────────────────
// Record the live panel at localhost:3000 while calling the agent from your
// phone, save it as  video/public/demo.mp4 , then flip this to true.
const HAS_RECORDING = false;

const FramedVideo: React.FC = () => (
  <div style={{borderRadius: 20, overflow: 'hidden', border: `1px solid ${theme.border}`, background: theme.bgElevated, boxShadow: '0 40px 120px rgba(0,0,0,0.6)'}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 10, padding: '16px 22px', background: '#101216', borderBottom: `1px solid ${theme.border}`}}>
      <div style={{width: 14, height: 14, borderRadius: 7, background: '#FF5F57'}} />
      <div style={{width: 14, height: 14, borderRadius: 7, background: '#FEBC2E'}} />
      <div style={{width: 14, height: 14, borderRadius: 7, background: '#28C840'}} />
      <div style={{marginLeft: 18, color: theme.textMuted, fontSize: 22}}>amparo-ai · live coverage comparison</div>
    </div>
    <OffthreadVideo src={staticFile('demo.mp4')} style={{width: '100%', display: 'block'}} />
  </div>
);

export const DemoScene: React.FC = () => {
  return (
    <Background glow={theme.green}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: FONT, padding: 80}}>
        <SlideIn direction="up" delay={2} style={{width: '100%'}}>
          {HAS_RECORDING ? (
            <FramedVideo />
          ) : (
            <Panel countersDelay={8} trapDelay={150} plansDelay={162} citeDelay={366} />
          )}
        </SlideIn>
      </AbsoluteFill>
    </Background>
  );
};
