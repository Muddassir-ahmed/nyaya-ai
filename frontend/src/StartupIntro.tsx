import { useEffect, useRef } from 'react';

import './startup-intro.css';

export const STARTUP_INTRO_SESSION_KEY = 'nyaya-ai-startup-intro-complete';

type StartupIntroProps = {
  onComplete: () => void;
};

async function playWhoosh() {
  const AudioContextClass =
    window.AudioContext ||
    (window as typeof window & {
      webkitAudioContext?: typeof AudioContext;
    }).webkitAudioContext;

  if (!AudioContextClass) return false;

  try {
    const context = new AudioContextClass();
    await context.resume();

    if (context.state !== 'running') {
      await context.close();
      return false;
    }

    const duration = 3.35;
    const buffer = context.createBuffer(
      1,
      Math.floor(context.sampleRate * duration),
      context.sampleRate,
    );
    const data = buffer.getChannelData(0);

    for (let index = 0; index < data.length; index += 1) {
      const progress = index / data.length;
      const envelope = Math.sin(Math.PI * progress) ** 1.7;
      data[index] = (Math.random() * 2 - 1) * envelope;
    }

    const source = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gain = context.createGain();

    source.buffer = buffer;
    filter.type = 'bandpass';
    filter.Q.value = 0.7;
    filter.frequency.setValueAtTime(280, context.currentTime);
    filter.frequency.exponentialRampToValueAtTime(
      1800,
      context.currentTime + duration * 0.48,
    );
    filter.frequency.exponentialRampToValueAtTime(
      360,
      context.currentTime + duration,
    );
    gain.gain.setValueAtTime(0, context.currentTime);
    gain.gain.linearRampToValueAtTime(0.055, context.currentTime + 0.55);
    gain.gain.linearRampToValueAtTime(0.045, context.currentTime + 2.45);
    gain.gain.linearRampToValueAtTime(0, context.currentTime + duration);
    source.connect(filter).connect(gain).connect(context.destination);
    source.start();
    source.stop(context.currentTime + duration);
    source.addEventListener('ended', () => void context.close());
    return true;
  } catch {
    return false;
  }
}

function StateEmblem() {
  return (
    <span
      className="startup-emblem"
      role="img"
      aria-label="State Emblem of India"
    />
  );
}

export function StartupIntro({ onComplete }: StartupIntroProps) {
  const played = useRef(false);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;

    if (reduceMotion) {
      const quickExit = window.setTimeout(onComplete, 700);
      return () => {
        document.body.style.overflow = previousOverflow;
        window.clearTimeout(quickExit);
      };
    }

    const trySound = () => {
      if (played.current) return;
      void playWhoosh().then((didPlay) => {
        played.current = didPlay;
      });
    };

    const soundTimer = window.setTimeout(trySound, 900);
    const finishTimer = window.setTimeout(onComplete, 6750);

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onComplete();
    };

    window.addEventListener('pointerdown', trySound, { once: true });
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.clearTimeout(soundTimer);
      window.clearTimeout(finishTimer);
      window.removeEventListener('pointerdown', trySound);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onComplete]);

  return (
    <section className="startup-intro" aria-label="NyayaAI introduction">
      <div className="startup-color-wash" aria-hidden="true">
        <span className="startup-color-wash__saffron" />
        <span className="startup-color-wash__navy" />
        <span className="startup-color-wash__green" />
        <span className="startup-color-wash__gold" />
      </div>

      <div className="startup-intro__emblem">
        <div className="startup-intro__orbit" aria-hidden="true" />
        <StateEmblem />
      </div>

      <div className="startup-intro__name" aria-label="NyayaAI">
        <span>NYAYA</span>
        <strong>AI</strong>
      </div>

      <button
        className="startup-intro__skip"
        type="button"
        onClick={onComplete}
      >
        Skip intro
      </button>
    </section>
  );
}
