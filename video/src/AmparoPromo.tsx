import React from 'react';
import {Audio, Sequence, staticFile} from 'remotion';
import {springTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import {BEATS, sceneDur, TRANSITION} from './beats';
import {Captions} from './components/Captions';
import {HookScene} from './scenes/HookScene';
import {ProblemScene} from './scenes/ProblemScene';
import {TitleScene} from './scenes/TitleScene';
import {DemoScene} from './scenes/DemoScene';
import {CallScene} from './scenes/CallScene';
import {OutroScene} from './scenes/OutroScene';

// Drop a royalty-free track at public/music.mp3 and flip this to true.
const HAS_MUSIC = false;

type SlideDir = 'from-left' | 'from-right' | 'from-top' | 'from-bottom';
const eased = springTiming({durationInFrames: TRANSITION, config: {damping: 200}});
const slideT = (direction: SlideDir) => ({presentation: slide({direction}), timing: eased});

export const AmparoPromo: React.FC = () => {
  return (
    <>
      {HAS_MUSIC ? <Audio src={staticFile('music.mp3')} volume={0.14} /> : null}

      {/* Voiceover — one clip per beat, placed at its absolute frame so speech,
          captions, and visuals stay in sync. */}
      {BEATS.map((b) => (
        <Sequence key={b.clip} from={b.at} durationInFrames={b.dur + 8}>
          <Audio src={staticFile(`vo/${b.clip}`)} />
        </Sequence>
      ))}

      {/* Visuals */}
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={sceneDur('hook')}>
          <HookScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition {...slideT('from-right')} />

        <TransitionSeries.Sequence durationInFrames={sceneDur('problem')}>
          <ProblemScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition {...slideT('from-bottom')} />

        <TransitionSeries.Sequence durationInFrames={sceneDur('reveal')}>
          <TitleScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition {...slideT('from-right')} />

        <TransitionSeries.Sequence durationInFrames={sceneDur('demo')}>
          <DemoScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition {...slideT('from-bottom')} />

        <TransitionSeries.Sequence durationInFrames={sceneDur('call')}>
          <CallScene />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={eased} />

        <TransitionSeries.Sequence durationInFrames={sceneDur('outro')}>
          <OutroScene />
        </TransitionSeries.Sequence>
      </TransitionSeries>

      {/* Synced caption overlay (above everything). */}
      <Captions />
    </>
  );
};
