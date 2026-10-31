"""Music engine v2 — higher-quality original soundtracks (no samples, no copyright risk).

Physically-inspired instruments (Karplus-Strong strings with fractional tuning and body
resonances, inharmonic additive piano, reeds, bowed strings with vibrato and formants,
modal mallets), humanised timing/velocity, stereo placement, convolution reverb with
pre-delay, bus EQ/compression and a soft master limiter.

Songs are written in music_pro_songs.py with a small text notation:
  melody  "E5/2 D5/1 C5/1 r/2"   note/length in eighths (r = rest, /0.5 = sixteenth)
  chords  "Am9 F G Cmaj7"        one chord per bar unless given as "Am9/2" (beats)
"""
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, iirpeak, lfilter, sosfilt

SR = 44100
_rng = np.random.default_rng(1234)

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    """'C#4' -> 61, numbers pass through."""
    if isinstance(name, (int, float)):
        return name
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", name)
    n = NOTE[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]
    return n + 12 * (int(m.group(3)) + 1)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def T(d):
    return np.arange(max(1, int(d * SR))) / SR


# ------------------------------------------------------------------ filters
def lp(x, f, order=2):
    return sosfilt(butter(order, min(f, SR * 0.45), "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x)


def peak(x, f, q, gain):
    b, a = iirpeak(f, q, fs=SR)
    return x + gain * lfilter(b, a, x)


def adsr(n, a, d, s, r, dur):
    t = np.arange(n) / SR
    env = np.where(t < a, t / max(a, 1e-4),
                   np.where(t < a + d, 1 - (1 - s) * (t - a) / max(d, 1e-4), s))
    rel = np.clip((dur - t) / max(r, 1e-4), 0, 1) if r else 1
    return env * rel


# ------------------------------------------------------------------ plucked strings
def ks(m, dur, vel=1.0, bright=0.6, decay=0.996, pos=0.18, ring=0.0):
    """Karplus-Strong with allpass fractional delay so high notes stay in tune."""
    f = hz(m)
    P = SR / f
    N = int(math.floor(P - 0.5 - 0.1))
    d = P - 0.5 - N
    c = (1 - d) / (1 + d)
    n = int((dur + ring + 0.05) * SR)
    burst = _rng.uniform(-1, 1, N + 2)
    burst = lp(burst, 1500 + 9000 * bright * vel, 1)
    k = max(1, int(pos * N))
    burst = burst - np.roll(burst, k)  # pluck position comb
    x = np.zeros(n)
    x[: len(burst)] = burst
    g = decay ** (440 / max(f, 60))  # higher strings decay a little faster
    a = np.zeros(N + 3)
    a[0], a[1] = 1.0, c
    a[N] += -g / 2 * c
    a[N + 1] += -g / 2 * (1 + c)
    a[N + 2] += -g / 2
    y = lfilter([1.0, c], a, x)
    t = np.arange(n) / SR
    y *= np.clip((dur + ring - t) / 0.06, 0, 1)
    return y * vel * 0.5


def guitar(m, dur, vel=1.0, bright=0.55, steel=False):
    y = ks(m, dur, vel, bright + (0.2 if steel else 0), 0.997 if steel else 0.995, 0.14)
    y = peak(y, 110, 4, 0.8)
    y = peak(y, 230, 5, 0.5)
    return lp(y, 7000 if steel else 4500)


def harp(m, dur, vel=1.0):
    return lp(ks(m, dur + 0.8, vel, 0.4, 0.9985, 0.5), 5000) * 1.1


def harpsichord(m, dur, vel=1.0):
    y = ks(m, dur, vel, 1.0, 0.996, 0.08) + 0.5 * ks(m + 12, dur, vel, 1.0, 0.994, 0.1)
    return hp(y, 150) * 0.8


def mandolin(m, dur, vel=1.0, trem=12.0):
    """Tremolo picking: repeated short plucks."""
    n = int(dur * SR) + int(0.3 * SR)
    out = np.zeros(n)
    step = 1 / trem
    t = 0.0
    i = 0
    while t < dur:
        v = vel * (0.75 + 0.25 * (i % 2 == 0)) * (0.9 + 0.1 * _rng.random())
        s = ks(m, step * 1.6, v, 0.8, 0.993, 0.12)
        j = int(t * SR)
        out[j:j + len(s)] += s[: n - j]
        t += step
        i += 1
    return peak(out, 400, 3, 0.4) * 0.8


def bouzouki(m, dur, vel=1.0):
    y = ks(m, dur, vel, 0.9, 0.996, 0.1) + 0.6 * ks(m + 12, dur, vel, 0.9, 0.995, 0.1)
    return peak(hp(y, 180), 900, 3, 0.4)


def tar(m, dur, vel=1.0, slide_from=None):
    """Bright metal string with gentle vibrato, optional grace slide (mugham-style)."""
    y = ks(m, dur, vel, 0.95, 0.997, 0.09)
    t = np.arange(len(y)) / SR
    # vibrato by tiny resampling wobble
    wob = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) / 0.3, 0, 1)
    idx = np.cumsum(wob)
    idx = np.clip(idx, 0, len(y) - 1)
    y = np.interp(idx, np.arange(len(y)), y)
    if slide_from is not None:
        g = ks(slide_from, 0.09, vel * 0.6, 0.95)
        y[: len(g)] += g * np.linspace(1, 0, len(g))
    return peak(hp(y, 200), 1200, 2.5, 0.6) * 0.9


def ukulele(m, dur, vel=1.0):
    return peak(ks(m, dur, vel, 0.6, 0.992, 0.2), 350, 3, 0.6)


# ------------------------------------------------------------------ keys
def piano(m, dur, vel=1.0, felt=False):
    t = T(dur + 0.6)
    f = hz(m)
    B = 0.0004 * (1 + (m - 60) / 40)  # inharmonicity
    s = np.zeros_like(t)
    nparts = 10 if not felt else 6
    for k in range(1, nparts + 1):
        fk = f * k * math.sqrt(1 + B * k * k)
        if fk > SR * 0.45:
            break
        amp = (1 / k ** (1.1 if not felt else 1.6)) * (0.6 + 0.4 * vel) ** (k * 0.3)
        dec = 0.6 + 0.35 * k + (m - 60) * 0.03
        detune = 1 + 0.0007 * _rng.standard_normal()
        s += amp * (np.sin(2 * np.pi * fk * t) + 0.5 * np.sin(2 * np.pi * fk * detune * t)) * np.exp(-t * dec)
    s += 0.3 * np.sin(2 * np.pi * f * t) * np.exp(-t * 0.35)  # long fundamental "bloom"
    ham = lp(_rng.standard_normal(len(t)), 2500 if felt else 5000) * np.exp(-t * 90) * 0.15 * vel
    s = (s + ham) * np.minimum(t / 0.002, 1)
    s *= np.clip((dur + 0.25 - t) / 0.25, 0, 1)  # damper
    if felt:
        s = lp(s, 1800 + 1500 * vel)
    return s * vel * 0.13


def rhodes(m, dur, vel=1.0):
    t = T(dur + 0.4)
    f = hz(m)
    mod = (1.0 + 2.2 * vel) * np.exp(-t * 6)
    s = np.sin(2 * np.pi * f * t + mod * np.sin(2 * np.pi * f * t))
    s += 0.35 * np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 40) * vel  # tine bell
    s *= np.exp(-t * 1.1) * np.clip((dur + 0.2 - t) / 0.2, 0, 1) * np.minimum(t / 0.002, 1)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    return s * trem * vel * 0.16


def celesta(m, dur, vel=1.0):
    t = T(dur + 1.0)
    f = hz(m)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dd)
            for r, a, dd in ((1, 1, 1.6), (4.0, 0.3, 5), (10.2, 0.08, 12)))
    return s * np.minimum(t / 0.001, 1) * vel * 0.12


def musicbox(m, dur, vel=1.0):
    t = T(1.6)
    f = hz(m)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dd)
            for r, a, dd in ((1, 1, 2.4), (3.0, 0.35, 6), (5.4, 0.2, 9), (8.9, 0.08, 14)))
    return s * np.minimum(t / 0.0008, 1) * vel * 0.11


def glock(m, dur, vel=1.0):
    t = T(1.4)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + 0.25 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
    return s * np.minimum(t / 0.0006, 1) * vel * 0.11


def marimba(m, dur, vel=1.0):
    t = T(min(1.2, dur + 0.6))
    f = hz(m)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 5) + 0.4 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 18)
         + 0.1 * np.sin(2 * np.pi * f * 9.9 * t) * np.exp(-t * 40))
    return s * np.minimum(t / 0.001, 1) * vel * 0.2


def vibes(m, dur, vel=1.0):
    t = T(dur + 1.2)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 1.0) + 0.2 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 4)
    s *= 1 + 0.25 * np.sin(2 * np.pi * 5 * t)
    return s * np.minimum(t / 0.002, 1) * np.clip((dur + 0.6 - t) / 0.6, 0, 1) * vel * 0.13


# ------------------------------------------------------------------ sustained
def _saw(f, t, phase=None):
    p = (f * t + (phase if phase is not None else _rng.random())) % 1.0
    return 2 * p - 1


def _vib_freq(f, t, depth=0.006, rate=5.5, delay=0.25):
    return f * (1 + depth * np.sin(2 * np.pi * rate * t + _rng.random() * 6) * np.clip((t - delay) / 0.4, 0, 1))


def _osc(freq_t):
    return np.cumsum(freq_t) / SR


def strings(notes, dur, vel=1.0, att=0.5, rel=0.6, bright=2800):
    t = T(dur + rel)
    s = np.zeros_like(t)
    for m in notes:
        for d in (-0.003, 0.0, 0.004):
            ph = _osc(_vib_freq(hz(m) * (1 + d), t, 0.004, 5.2, 0.1))
            s += 2 * ((ph + _rng.random()) % 1.0) - 1
    s = lp(s, bright, 2)
    s = peak(s, 700, 1.5, 0.3)
    env = np.minimum(t / att, 1) * np.clip((dur + rel - t) / rel, 0, 1)
    return s * env * vel * 0.02


def violin(m, dur, vel=1.0, att=0.08):
    t = T(dur + 0.25)
    ph = _osc(_vib_freq(hz(m), t, 0.0065, 5.8, 0.15))
    s = 2 * ((ph + 0.1) % 1.0) - 1
    s = bp(s, 200, 7000)
    for f0, g in ((450, 1.0), (1500, 0.8), (2700, 0.6)):  # body formants
        s = peak(s, f0, 2.5, g)
    bow = lp(_rng.standard_normal(len(t)), 4000) * 0.04
    env = np.minimum(t / att, 1) * np.clip((dur + 0.2 - t) / 0.2, 0, 1)
    return (s + bow) * env * vel * 0.05


def cello(m, dur, vel=1.0):
    t = T(dur + 0.3)
    ph = _osc(_vib_freq(hz(m), t, 0.005, 5.0, 0.2))
    s = 2 * ((ph + 0.3) % 1.0) - 1
    s = lp(peak(s, 300, 2, 1.0), 3000)
    env = np.minimum(t / 0.12, 1) * np.clip((dur + 0.25 - t) / 0.25, 0, 1)
    return s * env * vel * 0.07


def flute(m, dur, vel=1.0, breath=0.12):
    t = T(dur + 0.15)
    ph = _osc(_vib_freq(hz(m), t, 0.005, 5.0, 0.2))
    s = np.sin(2 * np.pi * ph) + 0.12 * np.sin(4 * np.pi * ph)
    nz = bp(_rng.standard_normal(len(t)), hz(m) * 0.8, hz(m) * 3) * breath
    env = np.minimum(t / 0.05, 1) * np.clip((dur + 0.1 - t) / 0.1, 0, 1)
    return (s + nz) * env * vel * 0.15


def panflute(m, dur, vel=1.0):
    t = T(dur + 0.2)
    ph = _osc(_vib_freq(hz(m), t, 0.004, 4.5, 0.1))
    s = np.sin(2 * np.pi * ph)
    nz = bp(_rng.standard_normal(len(t)), hz(m) * 0.9, hz(m) * 1.6) * 0.35
    chiff = hp(_rng.standard_normal(len(t)), 3000) * np.exp(-t * 60) * 0.3
    env = np.minimum(t / 0.03, 1) * np.clip((dur + 0.15 - t) / 0.15, 0, 1)
    return (s + nz + chiff) * env * vel * 0.16


def accordion(m, dur, vel=1.0):
    t = T(dur + 0.1)
    s = np.zeros_like(t)
    for d in (-0.0035, 0.0035):  # musette tuning
        ph = (hz(m) * (1 + d) * t + _rng.random()) % 1.0
        s += np.where(ph < 0.35, 1.0, -0.55)
    s = lp(peak(s, 1200, 2, 0.6), 4500)
    env = np.minimum(t / 0.04, 1) * np.clip((dur + 0.06 - t) / 0.06, 0, 1) * (1 + 0.06 * np.sin(2 * np.pi * 3 * t))
    return s * env * vel * 0.04


def pad(notes, dur, vel=1.0, att=1.0, bright=1500):
    t = T(dur + 1.0)
    s = np.zeros_like(t)
    for m in notes:
        for d in (-0.006, -0.002, 0.002, 0.006):
            s += _saw(hz(m) * (1 + d), t)
    s = lp(s, bright, 2)
    env = np.minimum(t / att, 1) * np.clip((dur + 1.0 - t) / 1.0, 0, 1)
    return s * env * vel * 0.012


def whistle(m, dur, vel=1.0):
    t = T(dur + 0.1)
    ph = _osc(_vib_freq(hz(m), t, 0.008, 6.0, 0.1))
    s = np.sin(2 * np.pi * ph) + bp(_rng.standard_normal(len(t)), hz(m) * 0.95, hz(m) * 1.05) * 0.2
    env = np.minimum(t / 0.03, 1) * np.clip((dur + 0.05 - t) / 0.06, 0, 1)
    return s * env * vel * 0.12


def brass(notes, dur, vel=1.0):
    t = T(dur + 0.2)
    s = np.zeros_like(t)
    for m in notes:
        s += _saw(hz(m), t) + _saw(hz(m) * 1.003, t)
    cut = 500 + 2500 * vel * np.minimum(t / 0.12, 1)
    # time-varying brightness approximated by blending two filters
    s = lp(s, 900) * (1 - np.minimum(t / 0.12, 1) * 0.6) + lp(s, 900 + 2200 * vel) * np.minimum(t / 0.12, 1) * 0.6
    env = np.minimum(t / 0.05, 1) * np.clip((dur + 0.15 - t) / 0.15, 0, 1)
    return s * env * vel * 0.03


# ------------------------------------------------------------------ bass
def upright(m, dur, vel=1.0):
    y = ks(m, dur, vel, 0.3, 0.996, 0.3)
    t = np.arange(len(y)) / SR
    y += 0.6 * np.sin(2 * np.pi * hz(m) * t) * np.exp(-t * 3) * vel
    return lp(peak(y, 90, 2, 0.6), 1500) * 1.2


def ebass(m, dur, vel=1.0):
    t = T(dur + 0.05)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    env = np.minimum(t / 0.005, 1) * np.exp(-t * 1.5) * np.clip((dur + 0.03 - t) / 0.04, 0, 1)
    return np.tanh(1.3 * s * env) * vel * 0.28


def subbass(m, dur, vel=1.0):
    t = T(dur + 0.05)
    s = np.sin(2 * np.pi * hz(m) * t)
    env = np.minimum(t / 0.01, 1) * np.clip((dur + 0.03 - t) / 0.05, 0, 1)
    return s * env * vel * 0.3


# ------------------------------------------------------------------ percussion (all soft)
def kick(vel=1.0, tone=52, punch=1.0):
    t = T(0.45)
    f = tone + 90 * punch * np.exp(-t * 35)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    click = hp(_rng.standard_normal(len(t)), 2000) * np.exp(-t * 300) * 0.15
    return (s + click) * vel * 0.55


def snare(vel=1.0, tone=185, snap=0.8):
    t = T(0.3)
    n = bp(_rng.standard_normal(len(t)), 1500, 9000) * np.exp(-t * 22) * snap
    b = np.sin(2 * np.pi * tone * t) * np.exp(-t * 30)
    return (n + 0.6 * b) * vel * 0.22


def rim(vel=1.0):
    t = T(0.08)
    return (np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 80) + bp(_rng.standard_normal(len(t)), 2000, 6000) * np.exp(-t * 120) * 0.5) * vel * 0.12


def clap(vel=1.0):
    t = T(0.3)
    n = bp(_rng.standard_normal(len(t)), 900, 6000)
    e = sum(np.exp(-np.maximum(t - d, 0) * 70) * (t >= d) for d in (0, 0.01, 0.021)) / 3 + np.exp(-t * 16) * 0.4
    return n * e * vel * 0.2


def snap(vel=1.0):
    t = T(0.12)
    return bp(_rng.standard_normal(len(t)), 1800, 7000) * np.exp(-t * 70) * vel * 0.2


def hat(vel=1.0, open_=False):
    t = T(0.3 if open_ else 0.07)
    n = hp(_rng.standard_normal(len(t)), 7500)
    return n * np.exp(-t * (12 if open_ else 65)) * vel * 0.06


def shaker(vel=1.0):
    t = T(0.09)
    n = bp(_rng.standard_normal(len(t)), 4000, 12000)
    return n * np.minimum(t / 0.015, 1) * np.exp(-t * 45) * vel * 0.06


def tamb(vel=1.0):
    t = T(0.25)
    jingles = sum(np.sin(2 * np.pi * f * t) for f in (5200, 6800, 8100, 9600)) * 0.2
    n = hp(_rng.standard_normal(len(t)), 6000)
    return (n + jingles) * np.exp(-t * 18) * vel * 0.05


def brush(vel=1.0, swish=False):
    t = T(0.35 if swish else 0.18)
    n = bp(_rng.standard_normal(len(t)), 2500, 9000)
    env = np.minimum(t / (0.08 if swish else 0.01), 1) * np.exp(-t * (8 if swish else 20))
    return n * env * vel * 0.06


def cajon(vel=1.0, slap=False):
    t = T(0.3)
    if slap:
        s = bp(_rng.standard_normal(len(t)), 1500, 7000) * np.exp(-t * 35) + np.sin(2 * np.pi * 320 * t) * np.exp(-t * 40) * 0.5
    else:
        s = np.sin(2 * np.pi * (75 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 12)
    return s * vel * 0.35


def timpani(m, vel=1.0):
    t = T(2.0)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 1.6) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t) * np.exp(-t * 2.5)
    s += lp(_rng.standard_normal(len(t)), 600) * np.exp(-t * 25) * 0.4
    return s * vel * 0.35


def daf(vel=1.0, low=True):
    t = T(0.5 if low else 0.15)
    if low:
        s = np.sin(2 * np.pi * (90 + 25 * np.exp(-t * 18)) * t) * np.exp(-t * 6)
        s += lp(_rng.standard_normal(len(t)), 1200) * np.exp(-t * 35) * 0.3
    else:
        s = bp(_rng.standard_normal(len(t)), 1500, 7000) * np.exp(-t * 45) + np.sin(2 * np.pi * 480 * t) * np.exp(-t * 35) * 0.3
    jing = hp(_rng.standard_normal(len(t)), 7000) * np.exp(-t * 14) * 0.15
    return (s + jing) * vel * 0.4


def swell(dur, vel=1.0):
    """Reverse-cymbal style swell (no harsh whoosh)."""
    t = T(dur)
    n = lp(hp(_rng.standard_normal(len(t)), 3000), 11000)
    return n * (t / dur) ** 3 * vel * 0.05


# ------------------------------------------------------------------ harmony helpers
QUAL = {
    "": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10],
    "9": [0, 4, 7, 10, 14], "m9": [0, 3, 7, 10, 14], "maj9": [0, 4, 7, 11, 14], "add9": [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14], "sus2": [0, 2, 7], "sus4": [0, 5, 7], "6": [0, 4, 7, 9], "m6": [0, 3, 7, 9],
    "dim": [0, 3, 6], "dim7": [0, 3, 6, 9], "m7b5": [0, 3, 6, 10], "7b9": [0, 4, 7, 10, 13],
    "7sus4": [0, 5, 7, 10], "6/9": [0, 4, 7, 9, 14], "aug": [0, 4, 8], "13": [0, 4, 10, 14, 21],
}


def parse_chord(name):
    m = re.fullmatch(r"([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?", name)
    root = midi(m.group(1) + "3") % 12
    q = QUAL[m.group(2)]
    bass = midi(m.group(3) + "3") % 12 if m.group(3) else root
    return root, [root + i for i in q], bass


def voicing(name, center=64, prev=None):
    """Close voicing near `center`, voice-led from previous voicing when given."""
    root, tones, _ = parse_chord(name)
    pcs = sorted({t % 12 for t in tones})
    best, best_cost = None, 1e9
    for low in range(center - 10, center + 3):
        v = []
        for pc in pcs:
            n = low + ((pc - low) % 12)
            v.append(n)
        v.sort()
        cost = abs(np.mean(v) - center) * 0.5
        if prev:
            cost += sum(min(abs(a - b) for b in prev) for a in v)
        if cost < best_cost:
            best, best_cost = v, cost
    return best


def bass_note(name, octave=2):
    _, _, b = parse_chord(name)
    return b + 12 * (octave + 1)


def chord_list(spec, beats_per_bar=4):
    """'Am9 F G/2 E7/2' -> [(name, beats)]"""
    out = []
    for tok in spec.split():
        if "/" in tok and tok.split("/")[-1].replace(".", "").isdigit():
            n, b = tok.rsplit("/", 1)
            out.append((n, float(b)))
        else:
            out.append((tok, float(beats_per_bar)))
    return out


def melody(spec):
    """'E5/2 D5/1 r/1' -> [(midi or None, eighths)]"""
    out = []
    for tok in spec.split():
        n, l = tok.split("/")
        out.append((None if n == "r" else midi(n), float(l)))
    return out


# ------------------------------------------------------------------ song / mixer
class Song:
    def __init__(self, bpm, dur=34.0, swing=0.0, beats_per_bar=4, human=0.008):
        self.bpm, self.b, self.dur = bpm, 60.0 / bpm, dur
        self.swing, self.bpb, self.human = swing, beats_per_bar, human
        n = int((dur + 3) * SR)
        self.buses = {}
        self.n = n
        self.duck = np.ones(n)

    @property
    def bars(self):
        return int(self.dur / (self.b * self.bpb))

    def t(self, bar, beat=0.0):
        whole = math.floor(beat + 1e-9)
        frac = beat - whole
        if self.swing and abs(frac - 0.5) < 1e-6:
            frac += self.swing
        return (bar * self.bpb + whole + frac) * self.b

    def put(self, bus, sig, at, gain=1.0, pan=0.0, human=True):
        if bus not in self.buses:
            self.buses[bus] = np.zeros((self.n, 2))
        if human and self.human:
            at += _rng.normal(0, self.human)
            gain *= 1 + _rng.normal(0, 0.06)
        i = int(round(at * SR))
        if i < 0:
            sig, i = sig[-i:], 0
        if i >= self.n:
            return
        k = min(len(sig), self.n - i)
        lg = math.cos((pan + 1) * math.pi / 4) * gain
        rg = math.sin((pan + 1) * math.pi / 4) * gain
        self.buses[bus][i:i + k, 0] += sig[:k] * lg
        self.buses[bus][i:i + k, 1] += sig[:k] * rg

    def sidechain(self, at, depth=0.3, length=None):
        length = length or self.b * 0.9
        i = int(at * SR)
        k = min(int(length * SR), self.n - i)
        if k > 0:
            self.duck[i:i + k] = np.minimum(self.duck[i:i + k], 1 - depth + depth * np.linspace(0, 1, k) ** 0.7)

    # ---- arrangement helpers
    def melody_line(self, inst, spec, bar, bus="lead", gain=1.0, pan=0.0, transpose=0, legato=1.0, **kw):
        pos = 0.0
        for m, l in melody(spec):
            if m is not None:
                beat = pos / 2
                b = bar + int(beat // self.bpb)
                self.put(bus, inst(m + transpose, l / 2 * self.b * legato, **kw), self.t(b, beat % self.bpb), gain, pan)
            pos += l
        return pos / 2 / self.bpb  # bars used


def reverb_ir(secs=2.2, predelay=0.02, damp=6000, seed=0, decay=3.0):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    t = np.arange(n) / SR
    irs = []
    for ch in range(2):
        noise = r.standard_normal(n) * np.exp(-t * decay)
        noise = lp(noise, damp)
        er = np.zeros(n)
        for k in range(8):  # early reflections
            er[int((0.007 + 0.011 * k + r.random() * 0.004) * SR)] = (0.6 - k * 0.06) * (1 if r.random() > 0.5 else -1)
        ir = np.concatenate([np.zeros(int(predelay * SR)), er * 0.6 + noise])
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    return irs


# melody first, harmony under it, rhythm further back (dB relative to the lead)
BUS_TARGET_DB = {"lead": 0, "keys": -6, "gtr": -6, "comp": -7, "bass": -8, "pad": -11,
                 "drums": -10, "brass": -10, "fx": -18}


def render(song, path, mix, master_lp=None, fade_in=0.3, fade_out=2.0):
    """mix: {bus: dict(gain, rev, hp, lp, duck)}; writes mp3 normalised to -14 LUFS."""
    n = song.n
    dry = np.zeros((n, 2))
    send = np.zeros((n, 2))
    for bus, x in song.buses.items():
        cfg = mix.get(bus, {})
        y = x.copy()
        # auto-balance: every bus to a fixed level relative to the melody; mix "gain" is a trim
        act = np.abs(y).sum(1) > 1e-5
        if act.any():
            rms = np.sqrt(np.mean(y[act] ** 2))
            y *= 10 ** (BUS_TARGET_DB.get(bus, -8) / 20) * 0.1 / rms
        for ch in range(2):
            if cfg.get("hp"):
                y[:, ch] = hp(y[:, ch], cfg["hp"])
            if cfg.get("lp"):
                y[:, ch] = lp(y[:, ch], cfg["lp"])
        if cfg.get("duck"):
            y *= (1 - cfg["duck"] + cfg["duck"] * song.duck)[:, None]
        y *= cfg.get("gain", 1.0)
        dry += y
        send += y * cfg.get("rev", 0.2)
    irs = reverb_ir(**mix.get("_reverb", {}))
    wet = np.stack([fftconvolve(send[:, c], irs[c])[:n] for c in range(2)], 1)
    out = dry + wet
    # gentle bus compression (RMS follower)
    rms = np.sqrt(lp(np.mean(out ** 2, 1), 8, 1).clip(1e-12))
    thr = np.percentile(rms, 70)
    gain = np.where(rms > thr, (thr / rms) ** 0.35, 1.0)
    out *= gain[:, None]
    if master_lp:
        out = np.stack([lp(out[:, c], master_lp) for c in range(2)], 1)
    L = int(song.dur * SR)
    out = out[:L]
    tt = np.arange(L) / SR
    out *= (np.clip(tt / fade_in, 0, 1) * np.clip((song.dur - tt) / fade_out, 0, 1))[:, None]
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.98
    out = np.tanh(out * 1.15) / np.tanh(1.15)
    path = Path(path)
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 0.95 * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", "loudnorm=I=-14:TP=-1.2:LRA=9",
                    "-ar", "44100", "-b:a", "224k", str(path)], check=True)
    wav.unlink()
    return path
