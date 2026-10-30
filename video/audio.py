"""Original soundtrack generator — no samples, no third-party music, so no copyright issues.

Everything is synthesised here from sine waves and noise: a warm "luxury lounge" groove
(FM electric piano, soft pad, sub bass, light drums) whose bars land exactly on the video's
cuts, plus a sound effect for every transition (whoosh for whip, low boom for punch,
shimmer for flash). The intro and the end card are calm so the loop back to the hook is smooth.
"""
import numpy as np

SR = 44100
rng = np.random.default_rng(7)

# A minor colour: Am9 – Fmaj9 – Cmaj7 – G(add9), one chord per shot
CHORDS = [
    [57, 60, 64, 67, 71],   # Am9
    [53, 57, 60, 64, 67],   # Fmaj9
    [48, 55, 59, 64, 67],   # Cmaj7
    [55, 59, 62, 67, 69],   # Gadd9
]
BASS = [45, 41, 36, 43]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def place(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def fft_filter(x, lo=None, hi=None):
    """Smooth band filter in the frequency domain (lo = highpass edge, hi = lowpass edge)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1 / (1 + (f / hi) ** 4)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * g, len(x))


def reverb(x, secs=2.2, mix=0.28):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = fft_filter(ir, lo=200, hi=6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    wet = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return x * (1 - mix) + wet * mix


# ---------------- instruments ----------------
def epiano(m, dur, vel=1.0):
    t = t_axis(dur)
    f = hz(m)
    idx = 1.6 * np.exp(-t * 5)
    s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    s += 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 7)
    env = np.minimum(t / 0.004, 1) * np.exp(-t * 1.6)
    rel = np.clip((dur - t) / 0.08, 0, 1)
    return s * env * rel * vel * 0.22


def pad(ms, dur):
    t = t_axis(dur)
    s = np.zeros_like(t)
    for m in ms:
        for d in (-0.07, 0.0, 0.07):
            f = hz(m + d)
            s += np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
            s += 0.3 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(t / 0.6, 1) * np.clip((dur - t) / 0.6, 0, 1)
    return fft_filter(s * env, hi=1800) * 0.018


def bass(m, dur):
    t = t_axis(dur)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(t / 0.01, 1) * np.exp(-t * 1.2) * np.clip((dur - t) / 0.05, 0, 1)
    return np.tanh(1.5 * s * env) * 0.30


def kick():
    t = t_axis(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) * 0.75


def clap():
    t = t_axis(0.25)
    s = fft_filter(rng.standard_normal(len(t)), lo=900, hi=5000)
    return s * np.exp(-t * 22) * 0.16


def hat(open_=False):
    t = t_axis(0.18 if open_ else 0.06)
    s = fft_filter(rng.standard_normal(len(t)), lo=7000)
    return s * np.exp(-t * (18 if open_ else 70)) * 0.09


def whoosh(dur=0.55):
    """Rising filtered noise that peaks at the end (place so the end hits the cut)."""
    t = t_axis(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(t)
    seg = 2048
    for i in range(0, len(t), seg):  # sweep the band upward
        k = i / len(t)
        out[i:i + seg] = fft_filter(n[i:i + seg], lo=300 + 2500 * k, hi=1200 + 9000 * k)
    env = (t / dur) ** 2.2
    return out * env * 0.55


def boom():
    t = t_axis(1.2)
    f = 38 + 60 * np.exp(-t * 9)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    s += fft_filter(rng.standard_normal(len(t)), hi=900) * np.exp(-t * 16) * 0.35
    return s * 0.55


def shimmer():
    t = t_axis(1.0)
    s = sum(np.sin(2 * np.pi * hz(m) * t) for m in (88, 91, 95, 100))
    s += fft_filter(rng.standard_normal(len(t)), lo=6000) * 0.4
    return s * np.minimum(t / 0.02, 1) * np.exp(-t * 3.5) * 0.06


def riser(dur):
    t = t_axis(dur)
    f = 300 * 2 ** (2.5 * t / dur)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.2
    s += fft_filter(rng.standard_normal(len(t)), lo=2000) * 0.5
    return s * (t / dur) ** 2 * 0.18


# ---------------- arrangement ----------------
def soundtrack(shots, tr, end_dur, out_wav):
    """shots: [(key, dur, motion, label, transition), ...] after pacing; writes a 16-bit wav."""
    starts, acc = [], 0.0
    for s in shots:
        starts.append(acc)
        acc += s[1]
    end_start = acc
    total = end_start + end_dur
    n = int(total * SR) + 1
    music = np.zeros(n)
    drums = np.zeros(n)
    fx = np.zeros(n)
    duck = np.ones(n)

    # intro (hook shot): pad + slow e-piano arpeggio + riser into the first cut
    hook = shots[0][1]
    place(music, pad(CHORDS[0], hook + 0.6), 0)
    arp = [57, 64, 67, 71, 72, 71, 67, 64]
    step = hook / 8
    for i, m in enumerate(arp):
        place(music, epiano(m + 12, step * 2.5, 0.8), i * step)
    place(fx, riser(1.0), hook - 1.0)

    # groove: one bar per shot, beats spread over the shot length
    for i in range(1, len(shots)):
        t0, d = starts[i], shots[i][1]
        beat = d / 4
        ch = CHORDS[(i - 1) % 4]
        place(music, pad(ch, d + 0.4), t0)
        place(music, bass(BASS[(i - 1) % 4], beat * 2.6), t0)
        place(music, bass(BASS[(i - 1) % 4] + 12 if i % 2 else BASS[(i - 1) % 4], beat * 1.2), t0 + beat * 2.5)
        # e-piano: chord stab on 1, syncopated stabs on the "and" of 2 and on 4
        for at, v in ((0, 1.0), (beat * 1.5, 0.6), (beat * 3, 0.7)):
            for m in ch[1:]:
                place(music, epiano(m + 12, beat * 1.4, v * 0.55), t0 + at)
        # top melody note per bar, gently moving
        mel = [76, 72, 71, 74][(i - 1) % 4]
        place(music, epiano(mel + 12, beat * 2, 0.7), t0 + beat * 2)
        # drums (last groove bar builds with extra hats)
        for b in range(4):
            bt = t0 + b * beat
            if b in (0, 2):
                place(drums, kick(), bt)
                k = int(bt * SR)
                m_ = min(n - k, int(0.25 * SR))
                duck[k:k + m_] = np.minimum(duck[k:k + m_], 0.55 + 0.45 * np.linspace(0, 1, m_))
            if b in (1, 3):
                place(drums, clap(), bt)
            place(drums, hat(), bt + beat / 2)
            place(drums, hat(open_=(b == 3)), bt + beat / 2 + (beat / 4 if i == len(shots) - 1 else 0))

    # transition sound effects, centred on the visual transition
    for i in range(1, len(shots)):
        t0, kind = starts[i], shots[i][4]
        if kind == "whip":
            place(fx, whoosh(0.45), t0 + tr * 0.5 - 0.45)
        elif kind == "punch":
            place(fx, boom(), t0)
        elif kind == "flash":
            place(fx, shimmer(), t0)
            place(fx, whoosh(0.35), t0 + tr * 0.5 - 0.35, 0.6)

    # end card: flash into it, drums drop, resolving chord + piano, fade for a clean loop
    place(fx, whoosh(0.5), end_start + tr * 0.5 - 0.5, 0.8)
    place(fx, shimmer(), end_start)
    place(fx, boom(), end_start, 0.7)
    place(music, pad(CHORDS[0], end_dur), end_start)
    place(music, bass(BASS[0], 2.4), end_start)
    for j, m in enumerate([69, 72, 76, 79, 83]):
        place(music, epiano(m + 12, 3.0, 0.7), end_start + 0.15 + j * 0.18)

    mix = 1.5 * reverb(music * duck) + 0.6 * drums + reverb(fx, 1.4, 0.2)
    fade = np.clip((total - np.arange(n) / SR) / 0.9, 0, 1)
    fade *= np.clip(np.arange(n) / SR / 0.05, 0, 1)
    mix = np.tanh(mix * fade * 1.2)
    mix /= np.max(np.abs(mix)) / 0.89
    stereo = np.stack([mix, np.roll(mix, int(0.012 * SR)) * 0.96 + mix * 0.04], axis=1)
    pcm = (stereo * 32767).astype("<i2")
    import wave
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_wav
