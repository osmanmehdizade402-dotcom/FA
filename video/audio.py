"""Original soundtrack generator — no samples, no third-party music, so no copyright issues.

Style: bright, upbeat "tropical house" in F major (I–V–vi–IV), the kind of feel-good groove
used for luxury real-estate reels. Everything is synthesised here: a plucked-string lead
(Karplus–Strong) carrying a catchy 4-bar hook with a dotted-eighth echo, warm piano chords,
a pumping pad, off-beat bass and soft house drums. Each video shot is exactly one bar, so the
chord changes and the kick land on every cut — no whoosh/transition sound effects (user rule).
The intro is soft and builds into the first cut; the end card resolves and fades for the loop.
"""
import wave

import numpy as np

SR = 44100
rng = np.random.default_rng(11)

# F – C – Dm – Bb
CHORDS = [[65, 69, 72, 77], [64, 67, 72, 76], [62, 65, 69, 74], [62, 65, 70, 74]]
ROOTS = [41, 36, 38, 34]
# catchy hook, 8 eighth-notes per bar (None = rest); answers itself every 4 bars
HOOK = [
    [69, None, 72, None, 74, 72, 69, None],
    [67, None, 72, None, 76, 74, 72, None],
    [77, None, 76, 74, None, 72, 69, None],
    [74, None, 72, None, 69, 67, 65, None],
]
HOOK_B = [  # higher, more excited answer used in the last cycle
    [81, None, 79, 77, None, 76, 77, None],
    [79, None, 76, None, 72, 74, 76, None],
    [77, None, 81, None, 79, 77, 74, None],
    [74, 76, 77, None, 72, None, 77, None],
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def place(buf, sig, at, gain=1.0):
    i = int(round(at * SR))
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= len(buf):
        return
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def fft_filter(x, lo=None, hi=None, order=4):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1 / (1 + (f / hi) ** order)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** order)
    return np.fft.irfft(X * g, len(x))


def reverb(x, secs=2.0, mix=0.22, seed=0):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.5)
    ir = fft_filter(ir, lo=250, hi=7000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    wet = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return x * (1 - mix) + wet * mix


# ---------------- instruments ----------------
def pluck(m, dur, vel=1.0, bright=0.5):
    """Karplus–Strong plucked string: bright attack that mellows naturally."""
    f = hz(m)
    p = int(SR / f)
    n = int(dur * SR)
    buf = fft_filter(rng.uniform(-1, 1, p * 8), hi=2000 + 6000 * bright)[:p]
    out = np.empty(n)
    out[:p] = buf
    decay = 0.996
    for i in range(p, n):  # tight loop, short notes only
        out[i] = decay * 0.5 * (out[i - p] + out[i - p + 1 if i - p + 1 < i else i - p])
    t = np.arange(n) / SR
    out *= np.clip((dur - t) / 0.03, 0, 1)
    return out * vel * 0.5


def piano(m, dur, vel=1.0):
    t = t_axis(dur)
    f = hz(m)
    s = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3)
         + 0.2 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 6))
    env = np.minimum(t / 0.003, 1) * np.exp(-t * 1.3) * np.clip((dur - t) / 0.1, 0, 1)
    return s * env * vel * 0.12


def pad(ms, dur):
    t = t_axis(dur)
    s = np.zeros_like(t)
    for m in ms:
        for d in (-0.08, 0.0, 0.08):
            ph = 2 * np.pi * hz(m + d) * t + rng.uniform(0, 6.28)
            s += 2 / np.pi * np.arctan(np.tan(ph / 2))  # saw-ish
    env = np.minimum(t / 0.15, 1) * np.clip((dur - t) / 0.2, 0, 1)
    return fft_filter(s * env, hi=1400, order=2) * 0.012


def sub_bass(m, dur):
    t = t_axis(dur)
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    env = np.minimum(t / 0.008, 1) * np.exp(-t * 4) * np.clip((dur - t) / 0.02, 0, 1)
    return np.tanh(2 * s * env) * 0.32


def kick():
    t = t_axis(0.35)
    f = 48 + 120 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.7


def clap():
    t = t_axis(0.3)
    n = fft_filter(rng.standard_normal(len(t)), lo=1000, hi=6000)
    env = sum(np.exp(-np.maximum(t - d, 0) * 60) * (t >= d) for d in (0, 0.011, 0.022)) / 3
    env += np.exp(-t * 14) * 0.5
    return n * env * 0.22


def shaker(acc=1.0):
    t = t_axis(0.07)
    n = fft_filter(rng.standard_normal(len(t)), lo=6000)
    return n * np.minimum(t / 0.01, 1) * np.exp(-t * 55) * 0.06 * acc


def open_hat():
    t = t_axis(0.22)
    return fft_filter(rng.standard_normal(len(t)), lo=8000) * np.exp(-t * 16) * 0.07


def snare_roll(dur):
    out = np.zeros(int(dur * SR))
    k = 16
    for j in range(k):
        place(out, clap(), dur * j / k, 0.25 + 0.75 * j / k)
    return out


# ---------------- arrangement ----------------
def soundtrack(shots, tr, end_dur, out_wav):
    starts, acc = [], 0.0
    for s in shots:
        starts.append(acc)
        acc += s[1]
    end_start = acc
    total = end_start + end_dur
    n = int(total * SR) + 1
    lead = np.zeros(n)
    keys = np.zeros(n)
    padb = np.zeros(n)
    bassb = np.zeros(n)
    drums = np.zeros(n)
    pump = np.ones(n)
    beat = shots[1][1] / 4 if len(shots) > 1 else 0.5
    e8 = beat / 2

    # ---- intro (hook shot): soft piano chords, filtered pad, melody pickup into the drop
    hook = shots[0][1]
    place(padb, pad(CHORDS[0], hook + 0.3), 0, 0.7)
    for j, m in enumerate([65, 69, 72, 77, 72, 69]):
        place(keys, piano(m, 1.8, 0.8), j * hook / 7)
    for j, m in enumerate([72, 74, 76]):  # "C–D–E" pickup lands on the first cut
        place(lead, pluck(m, 0.5, 0.8), hook - (3 - j) * e8)
    place(drums, snare_roll(1.0), hook - 1.0, 0.7)

    # ---- groove: one bar per shot
    nb = len(shots) - 1
    for b in range(nb):
        i = b + 1
        t0 = starts[i]
        c = b % 4
        full = b >= 4
        place(padb, pad(CHORDS[c], beat * 4 + 0.2), t0)
        for st, v in ((0, 1.0), (1.5, 0.6), (3, 0.75)):  # piano rhythm
            for m in CHORDS[c]:
                place(keys, piano(m, beat * 1.4, v), t0 + st * beat)
        for k in range(4):  # off-beat house bass
            place(bassb, sub_bass(ROOTS[c] + (12 if k == 3 and full else 0), e8 * 0.95), t0 + k * beat + e8)
        phrase = HOOK_B[c] if b >= 8 else HOOK[c]
        for j, m in enumerate(phrase):
            if m is not None:
                place(lead, pluck(m, e8 * 2.2, 0.95 if j % 2 == 0 else 0.75, 0.6 if b < 8 else 0.8), t0 + j * e8)
        for k in range(4):
            bt = t0 + k * beat
            place(drums, kick(), bt, 0.8 if not full else 1.0)
            ks = int(bt * SR)
            m_ = min(n - ks, int(beat * SR))
            pump[ks:ks + m_] = np.minimum(pump[ks:ks + m_], 0.35 + 0.65 * np.linspace(0, 1, m_) ** 0.6)
            if full and k in (1, 3):
                place(drums, clap(), bt)
            place(drums, open_hat(), bt + e8, 0.6 if full else 0.35)
            for s16 in range(4):
                place(drums, shaker(1.0 if s16 % 2 else 0.5), bt + s16 * beat / 4)
        if b == nb - 1:  # fill into the end card
            place(drums, snare_roll(beat * 2), t0 + beat * 2, 0.8)

    # ---- end card: big resolving F chord, hook tail, gentle fade for the loop
    place(drums, kick(), end_start)
    place(padb, pad(CHORDS[0], end_dur), end_start, 1.2)
    place(bassb, sub_bass(ROOTS[0], 1.5), end_start)
    for m in CHORDS[0] + [81]:
        place(keys, piano(m, end_dur, 1.0), end_start)
    for j, m in enumerate([77, 76, 72, 69, 72, 77]):
        place(lead, pluck(m, 0.9, 0.8 - j * 0.08), end_start + 0.2 + j * beat)

    # ---- mix (stereo): lead with ping-pong dotted-eighth echo, pumping pad/bass
    d = int(e8 * 1.5 * SR)
    echo_l = np.zeros(n)
    echo_r = np.zeros(n)
    echo_l[d:] = lead[:-d] * 0.32
    echo_r[2 * d:] = lead[:-2 * d] * 0.22
    lead_l = reverb(lead + echo_l, 1.6, 0.25, 1)
    lead_r = reverb(lead + echo_r, 1.6, 0.25, 2)
    bed = reverb(keys * 0.9 + padb * pump, 2.2, 0.28, 3)
    bass_m = bassb * pump
    dr = reverb(drums, 0.8, 0.08, 4)
    L = 1.15 * lead_l + bed + 0.75 * bass_m + 0.55 * dr
    R = 1.15 * lead_r + np.roll(bed, int(0.009 * SR)) + 0.75 * bass_m + 0.55 * dr
    tt = np.arange(n) / SR
    fade = np.clip((total - tt) / 1.2, 0, 1) * np.clip(tt / 0.03, 0, 1)
    st = np.stack([L, R], axis=1) * fade[:, None]
    st = np.tanh(st * 1.3)
    st /= np.max(np.abs(st)) / 0.9
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    return out_wav
