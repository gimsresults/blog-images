"""Generate an original, royalty-free lo-fi music bed (WAV) for reels.

Usage: python3 scripts/music_bed.py out.wav seconds [bpm] [seed]
Soft kick/clap/hats + a warm minor pad progression. Mixed low on purpose:
it sits under the voice, it is never the star.
"""
import sys
import wave

import numpy as np

OUT, SECS = sys.argv[1], float(sys.argv[2])
BPM = float(sys.argv[3]) if len(sys.argv) > 3 else 96
rng = np.random.default_rng(int(sys.argv[4]) if len(sys.argv) > 4 else 7)
SR = 44100
N = int(SECS * SR)
beat = 60 / BPM
mix = np.zeros((N, 2))


def add(sig, at, gain=1.0, pan=0.0):
    i = max(0, int(at * SR))
    if i >= N:
        return
    sig = sig[: N - i]
    mix[i:i + len(sig), 0] += sig * gain * (1 - max(pan, 0))
    mix[i:i + len(sig), 1] += sig * gain * (1 + min(pan, 0))


def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.12)


def clap():
    n = int(0.25 * SR)
    noise = rng.normal(0, 1, n)
    noise = np.convolve(noise, np.ones(6) / 6, "same")
    return noise * env(n, 0.003, 0.07) * 0.5


def hat():
    n = int(0.06 * SR)
    noise = rng.normal(0, 1, n)
    noise = noise - np.convolve(noise, np.ones(4) / 4, "same")
    return noise * env(n, 0.001, 0.018) * 0.35


def pad(freqs, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for f in freqs:
        for det in (-0.6, 0.6):
            s += np.sin(2 * np.pi * (f + det) * t) + 0.25 * np.sin(4 * np.pi * (f + det) * t)
    a = np.minimum(t / 0.35, 1) * np.minimum((length - t) / 0.4, 1)
    s = s * np.clip(a, 0, 1) / (len(freqs) * 2)
    k = np.ones(40) / 40  # soften
    return np.convolve(s, k, "same")


def hz(note):  # midi -> hz
    return 440 * 2 ** ((note - 69) / 12)


chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
bar = 4 * beat
t = 0.0
b = 0
while t < SECS:
    add(pad([hz(n) for n in chords[b % 4]], bar + 0.3), t, 0.55)
    add(pad([hz(chords[b % 4][0] - 12)], bar), t, 0.35)  # bass
    for q in range(4):
        bt = t + q * beat
        if q in (0, 2):
            add(kick(), bt, 0.9)
        if q in (1, 3):
            add(clap(), bt, 0.6, pan=0.1)
        for e in (0, 0.5):
            add(hat(), bt + e * beat + rng.uniform(-0.004, 0.004), 0.5 if e else 0.35, pan=-0.2)
    t += bar
    b += 1

fade = int(1.5 * SR)
mix[:int(0.5 * SR)] *= np.linspace(0, 1, int(0.5 * SR))[:, None]
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
pcm = (mix * 0.8 * 32767).astype(np.int16)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(OUT, SECS, "s")
