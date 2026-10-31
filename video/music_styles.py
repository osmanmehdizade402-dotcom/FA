"""Ten original soundtrack styles for listing videos — all synthesised here, no samples,
so there is no copyright risk. Renders ~30 s previews so the user can pick one style.

Usage: python3 music_styles.py <out_dir>
"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from audio import SR, fft_filter, hz, place, reverb

rng = np.random.default_rng(5)
DUR = 30.0


def T(d):
    return np.arange(int(d * SR)) / SR


def env_ad(t, a, d, dur):
    return np.minimum(t / a, 1) * np.exp(-t * d) * np.clip((dur - t) / 0.04, 0, 1)


# ---------------- instruments (vectorised, fast) ----------------
def piano(m, dur, v=1.0, bright=1.0):
    t = T(dur)
    f = hz(m)
    s = sum((1 / k ** 1.3) * np.sin(2 * np.pi * k * f * t * (1 + 0.0004 * k)) * np.exp(-t * (0.9 + k * 0.7 / bright))
            for k in range(1, 7))
    return s * env_ad(t, 0.002, 0.6, dur) * v * 0.16


def epiano(m, dur, v=1.0, wow=0.0):
    t = T(dur)
    f = hz(m) * (1 + wow * np.sin(2 * np.pi * 0.6 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph + 1.4 * np.exp(-t * 4) * np.sin(ph)) + 0.2 * np.sin(2 * ph) * np.exp(-t * 6)
    return s * env_ad(t, 0.004, 1.4, dur) * v * 0.18


def pluck(m, dur, v=1.0, bright=1.0):
    t = T(dur)
    f = hz(m)
    s = sum((1 / k) * np.sin(2 * np.pi * k * f * t) * np.exp(-t * (2.5 + k * 2.2 * bright)) for k in range(1, 9))
    return s * np.minimum(t / 0.002, 1) * np.clip((dur - t) / 0.03, 0, 1) * v * 0.22


def saw(f, t, detune=0.0):
    ph = (f * (1 + detune)) * t + rng.uniform(0, 1)
    return 2 * (ph - np.floor(ph + 0.5))


def strings(ms, dur, v=1.0, att=0.8, cut=2600):
    t = T(dur)
    s = sum(saw(hz(m), t, d) for m in ms for d in (-0.004, 0, 0.004))
    s *= np.minimum(t / att, 1) * np.clip((dur - t) / 0.5, 0, 1)
    return fft_filter(s, hi=cut, order=2) * v * 0.012


def supersaw(ms, dur, v=1.0, cut=5000):
    t = T(dur)
    s = sum(saw(hz(m), t, d) for m in ms for d in (-0.012, -0.006, 0, 0.006, 0.012))
    s *= np.minimum(t / 0.01, 1) * np.clip((dur - t) / 0.05, 0, 1)
    return fft_filter(s, hi=cut, order=2) * v * 0.009


def bell(m, dur, v=1.0):
    t = T(dur)
    f = hz(m)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in
            ((1, 1, 1.2), (2.76, 0.5, 2.5), (5.4, 0.25, 4), (8.93, 0.12, 6)))
    return s * np.minimum(t / 0.002, 1) * np.clip((dur - t) / 0.05, 0, 1) * v * 0.12


def lead(m, dur, v=1.0, vib=0.006):
    t = T(dur)
    f = hz(m) * (1 + vib * np.sin(2 * np.pi * 5.5 * t) * np.minimum(t / 0.3, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) + 0.15 * np.sin(2 * ph)
    return s * np.minimum(t / 0.03, 1) * np.clip((dur - t) / 0.08, 0, 1) * v * 0.14


def brass(m, dur, v=1.0):
    t = T(dur)
    s = saw(hz(m), t) + saw(hz(m), t, 0.003)
    cut = 600 + 2400 * np.minimum(t / 0.15, 1)
    s = fft_filter(s, hi=2200, order=2)
    return s * np.minimum(t / 0.06, 1) * np.clip((dur - t) / 0.1, 0, 1) * v * 0.08


def bass(m, dur, v=1.0, drive=1.5):
    t = T(dur)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return np.tanh(drive * s * env_ad(t, 0.006, 2.5, dur)) * v * 0.3


def b808(m, dur, v=1.0):
    t = T(dur)
    f = hz(m) * (1 + 1.5 * np.exp(-t * 40))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return np.tanh(2.2 * s * env_ad(t, 0.003, 1.1, dur)) * v * 0.35


def kick(v=1.0, low=48):
    t = T(0.4)
    f = low + 120 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * v * 0.7


def snare(v=1.0, tone=190, decay=18):
    t = T(0.35)
    n = fft_filter(rng.standard_normal(len(t)), lo=1200, hi=8000)
    return (n * 0.8 + np.sin(2 * np.pi * tone * t) * 0.5) * np.exp(-t * decay) * v * 0.25


def clap(v=1.0):
    t = T(0.3)
    n = fft_filter(rng.standard_normal(len(t)), lo=1000, hi=6000)
    e = sum(np.exp(-np.maximum(t - d, 0) * 60) * (t >= d) for d in (0, 0.011, 0.022)) / 3 + np.exp(-t * 14) * 0.5
    return n * e * v * 0.22


def hat(v=1.0, open_=False):
    t = T(0.25 if open_ else 0.06)
    n = fft_filter(rng.standard_normal(len(t)), lo=7000)
    return n * np.exp(-t * (14 if open_ else 70)) * v * 0.07


def brush(v=1.0):
    t = T(0.22)
    n = fft_filter(rng.standard_normal(len(t)), lo=3000, hi=9000)
    return n * np.minimum(t / 0.02, 1) * np.exp(-t * 16) * v * 0.06


def taiko(v=1.0):
    t = T(1.2)
    f = 55 + 40 * np.exp(-t * 12)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.5)
    s += fft_filter(rng.standard_normal(len(t)), hi=500) * np.exp(-t * 20) * 0.5
    return s * v * 0.6


def frame_drum(low=True, v=1.0):
    t = T(0.5 if low else 0.12)
    if low:
        s = np.sin(2 * np.pi * (85 + 30 * np.exp(-t * 20)) * t) * np.exp(-t * 7)
        s += fft_filter(rng.standard_normal(len(t)), hi=1500) * np.exp(-t * 30) * 0.3
    else:
        s = fft_filter(rng.standard_normal(len(t)), lo=1800, hi=7000) * np.exp(-t * 45)
        s += np.sin(2 * np.pi * 420 * t) * np.exp(-t * 40) * 0.4
    return s * v * 0.45


def riser(dur, v=1.0):
    t = T(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    seg = 4096
    for i in range(0, len(t), seg):
        k = i / len(t)
        out[i:i + seg] = fft_filter(n[i:i + seg], lo=400 + 3000 * k, hi=1500 + 9000 * k)
    return out * (t / dur) ** 2 * v * 0.25


def crash(v=1.0):
    t = T(2.0)
    return fft_filter(rng.standard_normal(len(t)), lo=4000) * np.exp(-t * 2.2) * v * 0.12


# ---------------- helpers ----------------
class Song:
    def __init__(self, bpm, swing=0.0):
        self.bpm = bpm
        self.b = 60 / bpm
        self.swing = swing
        n = int((DUR + 3) * SR)
        self.bus = {k: np.zeros(n) for k in ("keys", "lead", "pad", "bass", "drums", "fx")}
        self.bars = int(DUR / (4 * self.b))

    def at(self, bar, beat):
        """Time of a beat position (beat may be fractional), with optional 8th swing."""
        whole = np.floor(beat)
        frac = beat - whole
        if self.swing and abs(frac - 0.5) < 1e-6:
            frac = 0.5 + self.swing
        return (bar * 4 + whole + frac) * self.b

    def put(self, bus, sig, t, g=1.0):
        place(self.bus[bus], sig, t, g)

    def pump(self, depth=0.6):
        n = len(self.bus["pad"])
        p = np.ones(n)
        step = int(self.b * SR)
        ramp = 1 - depth + depth * np.linspace(0, 1, step) ** 0.6
        for i in range(0, n - step, step):
            p[i:i + step] = ramp
        return p

    def render(self, path, rev=0.25, pump=None, lowpass=None, noise=0.0):
        B = self.bus
        p = pump if pump is not None else 1.0
        bed = reverb(B["keys"] + B["pad"] * p, 2.2, rev, 1)
        ld = reverb(B["lead"], 1.8, rev, 2)
        L = bed + ld * 1.0 + B["bass"] * p + B["drums"] + reverb(B["fx"], 1.5, 0.3, 3)
        R = np.roll(bed, int(0.011 * SR)) + np.roll(ld, int(0.007 * SR)) + B["bass"] * p + B["drums"] + reverb(B["fx"], 1.5, 0.3, 4)
        st = np.stack([L, R], 1)[: int(DUR * SR)]
        if lowpass:
            st = np.stack([fft_filter(st[:, 0], hi=lowpass), fft_filter(st[:, 1], hi=lowpass)], 1)
        if noise:
            hiss = fft_filter(rng.standard_normal(len(st)), lo=2000) * noise
            crack = (rng.random(len(st)) > 0.9997) * rng.uniform(-1, 1, len(st)) * noise * 25
            st += (hiss + crack)[:, None]
        tt = np.arange(len(st)) / SR
        st *= (np.clip(tt / 0.4, 0, 1) * np.clip((DUR - tt) / 2.0, 0, 1))[:, None]
        st = np.tanh(st * 1.2)
        st /= np.max(np.abs(st)) / 0.9
        wav = path.with_suffix(".wav")
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((st * 32767).astype("<i2").tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", "loudnorm=I=-14:TP=-1.0",
                        "-ar", "44100", "-b:a", "192k", str(path)], check=True)
        wav.unlink()


def chord_tones(root, kind):
    iv = {"maj": [0, 4, 7], "min": [0, 3, 7], "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10],
          "7": [0, 4, 7, 10], "maj9": [0, 4, 7, 11, 14], "min9": [0, 3, 7, 10, 14], "6": [0, 4, 7, 9],
          "add9": [0, 4, 7, 14]}[kind]
    return [root + i for i in iv]


# ---------------- the ten styles ----------------
def s01_piano(out):
    """Zərif fortepiano — sakit, emosional, lüks."""
    s = Song(72)
    prog = [(48, "maj"), (43, "maj"), (45, "min"), (41, "maj")]
    mel = [[76, 74, 72, 74], [74, 71, 67, 71], [72, 71, 69, 72], [69, 72, 77, 76]]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        ct = chord_tones(r + 12, k)
        s.put("keys", piano(r, s.b * 4, 0.9), s.at(bar, 0))
        s.put("keys", piano(r + 12, s.b * 3, 0.5), s.at(bar, 0))
        arp = [ct[0], ct[1], ct[2], ct[1] + 12, ct[2], ct[1] + 12, ct[0] + 12, ct[2]]
        for j, m in enumerate(arp):
            s.put("keys", piano(m + 12, s.b * 1.5, 0.45), s.at(bar, j * 0.5))
        if bar >= 2:
            for j, m in enumerate(mel[bar % 4]):
                s.put("lead", piano(m + 12, s.b * 1.6, 0.85 if j == 0 else 0.7, 1.3), s.at(bar, j))
    s.render(out, rev=0.38)


def s02_deep_house(out):
    """Deep House — gecə klubu lüksü, 122 BPM."""
    s = Song(122)
    prog = [(45, "min7"), (41, "maj7"), (48, "maj7"), (43, "6")]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        ct = chord_tones(r + 12, k)
        s.put("pad", strings(ct, s.b * 4, 0.8, 0.2, 1800), s.at(bar, 0))
        for st in (0.5, 1.75, 2.5, 3.5):
            for m in ct:
                s.put("keys", epiano(m + 12, s.b * 0.45, 0.55), s.at(bar, st))
        for k4 in range(4):
            s.put("drums", kick(1.0), s.at(bar, k4))
            s.put("drums", hat(0.8, True), s.at(bar, k4 + 0.5))
            for q in range(4):
                s.put("drums", hat(0.5 if q % 2 == 0 else 0.9), s.at(bar, k4 + q / 4))
            s.put("bass", bass(r, s.b * 0.45, 1.0), s.at(bar, k4 + 0.5))
        if bar % 2 == 1 or bar >= 4:
            s.put("drums", clap(0.9), s.at(bar, 1))
            s.put("drums", clap(0.9), s.at(bar, 3))
        if bar >= 8:
            motif = [[76, 72, 74], [72, 69, 72], [71, 67, 71], [74, 71, 74]][bar % 4]
            for j, m in enumerate(motif):
                s.put("lead", lead(m, s.b * 0.9, 0.8), s.at(bar, [0, 1.5, 3][j]))
    s.render(out, rev=0.22, pump=s.pump(0.55))


def s03_lofi(out):
    """Lo-fi Chill — isti, rahat, 'evdə qəhvə' əhval-ruhiyyəsi."""
    s = Song(80, swing=0.08)
    prog = [(53, "maj7"), (52, "min7"), (50, "min7"), (48, "maj7")]
    pent = [69, 72, 74, 76, 79, 81]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        for m in chord_tones(r, k):
            s.put("keys", epiano(m, s.b * 3.6, 0.65, wow=0.003), s.at(bar, 0) + rng.uniform(0, 0.02))
        for m in chord_tones(r, k)[1:]:
            s.put("keys", epiano(m, s.b * 1.2, 0.4, wow=0.003), s.at(bar, 2.5))
        s.put("bass", bass(r - 12, s.b * 1.8, 0.9, 1.0), s.at(bar, 0))
        s.put("bass", bass(r - 12 + 7, s.b * 0.9, 0.7, 1.0), s.at(bar, 2.5))
        s.put("drums", kick(0.9, 45), s.at(bar, 0))
        s.put("drums", kick(0.6, 45), s.at(bar, 2.5))
        s.put("drums", snare(0.8, 170, 14), s.at(bar, 1))
        s.put("drums", snare(0.8, 170, 14), s.at(bar, 3))
        for e in range(8):
            s.put("drums", hat(0.6 if e % 2 else 0.9), s.at(bar, e * 0.5))
        if bar >= 2:
            for j in range(3):
                s.put("lead", epiano(int(rng.choice(pent)) + 12, s.b * 1.2, 0.5), s.at(bar, [0.5, 1.5, 3][j]))
    s.render(out, rev=0.25, lowpass=4200, noise=0.012)


def s04_cinematic(out):
    """Kinematik — epik, böyük kino musiqisi hissi."""
    s = Song(90)
    prog = [(50, "min"), (46, "maj"), (53, "maj"), (48, "maj")]
    mel = [[74, 77, 76, 74], [74, 72, 70, 69], [72, 74, 77, 81], [79, 76, 72, 74]]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        ct = chord_tones(r, k)
        grow = min(1.0, 0.35 + bar / s.bars)
        s.put("pad", strings(ct + [ct[0] + 12, ct[1] + 12], s.b * 4.2, grow * 1.3, 0.6), s.at(bar, 0))
        s.put("bass", bass(r - 12, s.b * 4, 0.8, 1.2), s.at(bar, 0))
        for e in range(8):
            s.put("keys", pluck(r + (12 if e % 2 else 0), s.b * 0.5, 0.6 * grow, 0.6), s.at(bar, e * 0.5))
        if bar >= 4:
            s.put("drums", taiko(1.0), s.at(bar, 0))
            s.put("drums", taiko(0.6), s.at(bar, 2.5))
            s.put("drums", taiko(0.8), s.at(bar, 3))
        if bar >= 6:
            for j, m in enumerate(mel[bar % 4]):
                s.put("lead", brass(m - 12, s.b * 1.1, 1.0), s.at(bar, j))
                s.put("lead", strings([m], s.b * 1.1, 2.0, 0.08, 4000), s.at(bar, j))
        if bar in (3, s.bars - 5):
            s.put("fx", riser(s.b * 4, 1.0), s.at(bar, 0))
        if bar in (4, s.bars - 4):
            s.put("fx", crash(1.0), s.at(bar, 0))
    s.render(out, rev=0.4)


def s05_acoustic(out):
    """Akustik Pop — şən gitara, əl çalma və fit melodiyası."""
    s = Song(104)
    prog = [(55, "maj"), (50, "maj"), (52, "min"), (48, "maj")]
    strum = [(0, 1), (1, 1), (1.5, -1), (2.5, -1), (3, 1), (3.5, -1)]
    whistle = [[79, 81, 83, 79], [78, 76, 74, 78], [76, 79, 83, 81], [79, 76, 72, 74]]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        ct = chord_tones(r, k) + [r + 12, r + 16 if k == "maj" else r + 15]
        for pos, d in strum:
            notes = ct if d > 0 else ct[::-1]
            for j, m in enumerate(notes):
                s.put("keys", pluck(m, s.b * 1.2, 0.5 if d > 0 else 0.35, 1.2), s.at(bar, pos) + j * 0.012)
        s.put("bass", bass(r - 12, s.b * 1.8, 0.8, 1.0), s.at(bar, 0))
        s.put("bass", bass(r - 12 + 7, s.b * 1.8, 0.7, 1.0), s.at(bar, 2))
        s.put("drums", kick(0.8), s.at(bar, 0))
        s.put("drums", kick(0.6), s.at(bar, 2.5))
        s.put("drums", clap(1.0), s.at(bar, 1))
        s.put("drums", clap(1.0), s.at(bar, 3))
        for q in range(16):
            s.put("drums", hat(0.45 if q % 2 == 0 else 0.25), s.at(bar, q / 4))
        if bar >= 2:
            for j, m in enumerate(whistle[bar % 4]):
                s.put("lead", lead(m + 12, s.b * 0.9, 0.7, 0.012), s.at(bar, j))
    s.render(out, rev=0.2)


def s06_spa(out):
    """Ambient / Spa — çox sakit, su, zənglər, rahatlıq."""
    s = Song(60)
    prog = [(48, "maj9"), (45, "min9"), (41, "maj9"), (43, "6")]
    pent = [72, 74, 76, 79, 81, 84, 86, 88]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        s.put("pad", strings(chord_tones(r + 12, k), s.b * 4.6, 1.1, 1.8, 1500), s.at(bar, 0))
        s.put("bass", bass(r - 12, s.b * 4, 0.45, 0.8), s.at(bar, 0))
        for _ in range(3):
            s.put("lead", bell(int(rng.choice(pent)), 3.0, 0.7), s.at(bar, rng.choice([0, 1, 1.5, 2, 3, 3.5])))
    n = len(s.bus["fx"])
    water = fft_filter(rng.standard_normal(n), lo=600, hi=3000)
    water *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * np.arange(n) / SR) ** 2
    s.bus["fx"] += water * 0.02
    s.render(out, rev=0.5)


def s07_inspire(out):
    """Korporativ / İlhamverici — müsbət, motivasiya, uğur hissi."""
    s = Song(112)
    prog = [(48, "add9"), (47, "min"), (45, "min"), (41, "maj")]
    prog[1] = (43, "maj")
    mel = [[76, 79, 81, 79], [79, 74, 76, 74], [72, 76, 79, 81], [77, 76, 74, 72]]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        ct = chord_tones(r + 12, k)
        for e in range(8):
            for m in ct[:3]:
                s.put("keys", piano(m + 12, s.b * 0.6, 0.35 if e % 2 else 0.5), s.at(bar, e * 0.5))
        arp = ct[:3] + [ct[0] + 12]
        for q in range(16):
            s.put("lead", pluck(arp[q % 4] + 24, s.b * 0.3, 0.35, 1.5), s.at(bar, q / 4))
        s.put("bass", bass(r - 12, s.b * 2, 0.8), s.at(bar, 0))
        s.put("bass", bass(r - 12, s.b * 2, 0.7), s.at(bar, 2))
        if bar >= 2:
            for k4 in range(4):
                s.put("drums", kick(0.8), s.at(bar, k4))
        if bar >= 6:
            s.put("drums", clap(0.9), s.at(bar, 1))
            s.put("drums", clap(0.9), s.at(bar, 3))
            for j, m in enumerate(mel[bar % 4]):
                s.put("lead", bell(m + 12, s.b * 1.5, 0.9), s.at(bar, j))
        if bar == 5:
            for q in range(8):
                s.put("drums", snare(0.3 + q / 10), s.at(bar, 2 + q / 4))
            s.put("fx", crash(1.0), s.at(bar + 1, 0))
    s.render(out, rev=0.28)


def s08_jazz(out):
    """Caz Lounge — restoran/otel lobbisi kimi zərif caz."""
    s = Song(100, swing=0.12)
    prog = [(48, "min7"), (53, "7"), (46, "maj7"), (43, "7")]
    walk = [[36, 39, 43, 44], [41, 45, 48, 45], [46, 45, 43, 41], [43, 47, 50, 49]]
    vib = [[74, 75, 79, 82], [81, 77, 75, 72], [74, 77, 81, 79], [77, 74, 71, 74]]
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        ct = chord_tones(r + 12, k)
        for pos in (1.5, 3):
            for m in ct[1:] + [ct[0] + 12]:
                s.put("keys", epiano(m, s.b * 0.9, 0.5), s.at(bar, pos))
        for q, m in enumerate(walk[bar % 4]):
            s.put("bass", bass(m, s.b * 0.95, 0.9, 0.8), s.at(bar, q))
        for q in range(4):
            s.put("drums", brush(1.0), s.at(bar, q))
            if q % 2:
                s.put("drums", brush(0.7), s.at(bar, q + 0.5))
        s.put("drums", kick(0.35, 50), s.at(bar, 0))
        if bar >= 2:
            for j, m in enumerate(vib[bar % 4]):
                s.put("lead", bell(m, s.b * 1.6, 0.9), s.at(bar, j * 1.0 + (0.5 if j == 3 else 0)))
    s.render(out, rev=0.25)


def s09_oriental(out):
    """Şərq / Azərbaycan motivi — tar kimi melodiya, qaval ritmi, müasir bas."""
    s = Song(96)
    D = 62
    scale = [62, 63, 66, 67, 69, 70, 72, 74]  # D hicaz
    phrases = [[0, 1, 2, 1, 0, -1, 0, 0], [2, 3, 4, 3, 2, 1, 2, 2], [4, 5, 7, 5, 4, 3, 2, 1], [2, 1, 0, 1, 2, 1, 0, 0]]
    for bar in range(s.bars):
        s.put("pad", strings([D - 12, D - 5, D], s.b * 4.2, 1.0, 0.8, 1500), s.at(bar, 0))
        s.put("bass", bass(D - 24, s.b * 1.4, 0.9), s.at(bar, 0))
        s.put("bass", bass(D - 24 + 7, s.b * 0.9, 0.7), s.at(bar, 2.5))
        for pos, low in ((0, True), (1, False), (1.5, False), (2, True), (2.5, True), (3, False), (3.5, False)):
            s.put("drums", frame_drum(low, 1.0), s.at(bar, pos))
        if bar >= 4:
            s.put("drums", kick(0.7), s.at(bar, 0))
            s.put("drums", kick(0.7), s.at(bar, 2))
        if bar >= 1:
            ph = phrases[bar % 4]
            for j, idx in enumerate(ph):
                m = scale[idx] if idx >= 0 else 61
                s.put("lead", pluck(m, s.b * 0.6, 0.9, 0.8), s.at(bar, j * 0.5))
                if j in (2, 5):  # tremolo/trill ornament
                    for tr in range(3):
                        s.put("lead", pluck(m + (1 if tr % 2 == 0 else 0), s.b * 0.15, 0.4, 1.0),
                              s.at(bar, j * 0.5) + (tr + 1) * s.b / 8)
    s.render(out, rev=0.3)


def s10_future(out):
    """Future Bass / Trap — gənc, müasir, TikTok enerjisi."""
    s = Song(150)
    prog = [(53, "maj7"), (57, "min7"), (50, "min7"), (46, "maj7")]
    chops = [[77, 76, 72], [76, 72, 69], [74, 72, 69], [74, 77, 76]]
    drop = 4
    for bar in range(s.bars):
        r, k = prog[bar % 4]
        ct = chord_tones(r + 12, k)
        if bar < drop:
            s.put("keys", piano(ct[0], s.b * 4, 0.6), s.at(bar, 0))
            for m in ct[1:]:
                s.put("keys", piano(m, s.b * 4, 0.45), s.at(bar, 0))
            if bar == drop - 1:
                s.put("fx", riser(s.b * 4, 1.2), s.at(bar, 0))
                for q in range(16):
                    s.put("drums", snare(0.2 + q / 20), s.at(bar, q / 4))
            continue
        for pos, ln in ((0, 1.4), (1.5, 0.9), (2.5, 0.4), (3, 0.9)):
            s.put("pad", supersaw(ct, s.b * ln, 1.0), s.at(bar, pos))
        s.put("bass", b808(r - 24, s.b * 2.5, 1.0), s.at(bar, 0))
        s.put("bass", b808(r - 24, s.b * 1.2, 0.8), s.at(bar, 2.5))
        s.put("drums", kick(1.0), s.at(bar, 0))
        s.put("drums", kick(0.8), s.at(bar, 2.5))
        s.put("drums", clap(1.0), s.at(bar, 2))
        s.put("drums", snare(0.7), s.at(bar, 2))
        for q in range(8):
            s.put("drums", hat(0.8), s.at(bar, q / 2))
        if bar % 2:
            for q in range(6):
                s.put("drums", hat(0.6), s.at(bar, 3 + q / 6))
        for j, m in enumerate(chops[bar % 4]):
            s.put("lead", pluck(m + 12, s.b * 0.4, 0.9, 1.4), s.at(bar, [0.5, 1, 3.5][j]))
        if bar == drop:
            s.put("fx", crash(1.0), s.at(bar, 0))
    s.render(out, rev=0.22, pump=s.pump(0.7))


STYLES = [
    ("01-zerif-fortepiano", s01_piano),
    ("02-deep-house", s02_deep_house),
    ("03-lofi-chill", s03_lofi),
    ("04-kinematik-epik", s04_cinematic),
    ("05-akustik-pop", s05_acoustic),
    ("06-spa-ambient", s06_spa),
    ("07-ilhamverici", s07_inspire),
    ("08-caz-lounge", s08_jazz),
    ("09-serq-motivi", s09_oriental),
    ("10-future-bass", s10_future),
]

if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    only = sys.argv[2:] or None
    for name, fn in STYLES:
        if only and not any(name.startswith(o) for o in only):
            continue
        fn(out / f"{name}.mp3")
        print("ok", name)
