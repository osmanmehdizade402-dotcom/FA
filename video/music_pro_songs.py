"""Twenty original soundtracks for listing videos (all composed here — no copied melodies).

Each song is inspired by a European style (French musette, Italian bossa, Nordic piano,
Viennese salon, gypsy jazz, Balearic chill...) but every melody and progression is new.

Usage: python3 music_pro_songs.py <out_dir> [dur_seconds] [only-prefix ...]
"""
import sys
from pathlib import Path

import music_pro as M
from music_pro import Song

# ------------------------------------------------------------------ helpers


def bars_of(spec, bpb):
    """'Am F/2 G/2' -> per bar list of (chord, start_beat, beats)."""
    out, cur, pos = [], [], 0.0
    for name, beats in M.chord_list(spec, bpb):
        cur.append((name, pos, beats))
        pos += beats
        if pos >= bpb - 1e-6:
            out.append(cur)
            cur, pos = [], 0.0
    if cur:
        out.append(cur)
    return out


def section_plan(song, sections, order):
    """sections: {'A': (chords, melody_bars or None)}; order like 'IAAB...'; returns per-bar list."""
    plan = []
    i = 0
    while len(plan) < song.bars:
        key = order[i % len(order)]
        chords, mel = sections[key]
        cb = bars_of(chords, song.bpb)
        mb = [m.strip() for m in mel.split("|")] if mel else [None] * len(cb)
        for k in range(len(cb)):
            plan.append((key, cb[k], mb[k % len(mb)] if mb else None, k))
            if len(plan) >= song.bars:
                break
        i += 1
    return plan


def mel_bar(song, inst, spec, bar, bus="lead", gain=1.0, pan=0.0, transpose=0, legato=1.0, **kw):
    if not spec:
        return
    pos = 0.0
    for m, l in M.melody(spec):
        if m is not None:
            song.put(bus, inst(m + transpose, l / 2 * song.b * legato, **kw), song.t(bar, pos / 2), gain, pan)
        pos += l


def drums(song, bar, pattern, inst, bus="drums", gain=1.0, pan=0.0, steps=None, **kw):
    """pattern like 'x...o...x...o...' over one bar; x=1.0 o=0.6 -=0.35"""
    steps = steps or len(pattern)
    for i, ch in enumerate(pattern):
        v = {"x": 1.0, "o": 0.6, "-": 0.35}.get(ch)
        if v:
            song.put(bus, inst(vel=v, **kw), song.t(bar, i * song.bpb / steps), gain, pan)


def arp(song, inst, chord, bar, start, beats, pattern, center=60, step=0.5, bus="keys", gain=1.0, pan=0.0, ring=1.6, **kw):
    v = M.voicing(chord, center)
    root = M.bass_note(chord, 3)
    tones = [root] + v + [n + 12 for n in v]
    pos = 0.0
    k = 0
    while pos < beats - 1e-6:
        idx = pattern[k % len(pattern)]
        if idx is not None:
            n = tones[idx % len(tones)]
            song.put(bus, inst(n, step * song.b * ring, **kw), song.t(bar, start + pos), gain, pan)
        pos += step
        k += 1


def block(song, inst, chord, bar, beat, dur_beats, center=62, bus="keys", gain=1.0, pan=0.0, spread=0.0, **kw):
    for j, n in enumerate(M.voicing(chord, center)):
        song.put(bus, inst(n, dur_beats * song.b, **kw), song.t(bar, beat) + j * spread, gain, pan)


def strum(song, inst, chord, bar, beat, down=True, vel=1.0, center=55, bus="gtr", gain=1.0, pan=0.0, dur=1.2, speed=0.012):
    v = M.voicing(chord, center)
    v = [M.bass_note(chord, 2) + 12] + v + [v[0] + 12]
    if not down:
        v = v[::-1][:4]
    for j, n in enumerate(v):
        song.put(bus, inst(n, dur * song.b, vel=vel * (0.85 + 0.15 * (j == 0))), song.t(bar, beat) + j * speed, gain, pan)


def pad_bar(song, chord, bar, start, beats, center=60, inst=None, bus="pad", gain=1.0, **kw):
    inst = inst or M.strings
    song.put(bus, inst(M.voicing(chord, center), beats * song.b, **kw), song.t(bar, start), gain, human=False)


def bassline(song, inst, chord, bar, start, beats, pattern, octave=2, bus="bass", gain=1.0, **kw):
    """pattern: list of (beat, interval_semitones, len_beats) relative to chord bass."""
    b = M.bass_note(chord, octave)
    for at, iv, ln in pattern:
        if at < beats:
            song.put(bus, inst(b + iv, ln * song.b, **kw), song.t(bar, start + at), gain)


# ------------------------------------------------------------------ 1. Paris Café (musette waltz)
def s01_paris(out, dur):
    s = Song(168, dur, beats_per_bar=3, human=0.006)
    A = ("Am Am Dm Dm G7 G7 C E7",
         "E5/1 F5/1 E5/1 D#5/1 E5/2 | C6/4 B5/2 | A5/1 B5/1 A5/1 G#5/1 A5/2 | F5/4 r/2 | "
         "D5/1 E5/1 F5/1 G5/1 A5/2 | B5/2 A5/2 G5/2 | E5/4 G5/2 | B4/4 r/2")
    B = ("F F Am Am Dm E7 Am Am",
         "A5/3 G5/1 F5/2 | C6/4 A5/2 | E5/2 A5/2 C6/2 | B5/4 A5/2 | F5/2 A5/2 D6/2 | D6/2 C6/2 B5/2 | A5/6 | r/6")
    I = ("Am E7", None)
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"I": I, "A": A, "B": B}, "IAABA")):
        ch = chords[0][0]
        b = M.bass_note(ch, 2)
        s.put("bass", M.upright(b + (0 if bar % 2 == 0 else 7), s.b * 0.9), s.t(bar, 0), 1.0)
        for beat in (1, 2):
            block(s, M.accordion, ch, bar, beat, 0.55, center=58, bus="comp", gain=0.55, pan=-0.25)
            block(s, M.guitar, ch, bar, beat, 0.4, center=55, bus="gtr", gain=0.5, pan=0.3)
        s.put("drums", M.brush(0.8), s.t(bar, 0), 0.7, 0.1)
        s.put("drums", M.brush(0.5), s.t(bar, 1.5), 0.6, 0.1)
        if mel:
            mel_bar(s, M.accordion, mel, bar, gain=1.0, pan=0.08)
            if sec == "B":
                mel_bar(s, M.accordion, mel, bar, gain=0.35, pan=-0.1, transpose=-12)
    mix = {"lead": dict(gain=1.0, rev=0.22), "comp": dict(gain=0.8, rev=0.15), "gtr": dict(gain=0.8, rev=0.2),
           "bass": dict(gain=0.9, rev=0.05, lp=900), "drums": dict(gain=0.8, rev=0.1),
           "_reverb": dict(secs=1.6, predelay=0.015, decay=3.6)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 2. Riviera (Italian bossa)
def s02_riviera(out, dur):
    s = Song(132, dur, human=0.007)
    A = ("Cmaj7 Cmaj7 Dm7 G7 Em7 A7 Dm7 G7",
         "E5/3 G5/1 B5/4 | A5/2 G5/2 E5/4 | F5/3 A5/1 C6/2 A5/2 | B5/4 G5/4 | G5/3 B5/1 D6/4 | "
         "C#6/2 B5/2 A5/4 | F5/2 A5/2 G5/2 F5/2 | D5/8")
    B = ("Fmaj7 Fm6 Em7 A7 Dm7 G7 Cmaj7 Cmaj7",
         "A5/3 C6/1 E6/4 | D6/2 C6/2 Ab5/4 | G5/3 B5/1 D6/4 | C#6/2 E6/2 G5/4 | F5/2 E5/2 D5/2 F5/2 | "
         "B5/4 D6/4 | C6/8 | r/8")
    I = ("Cmaj7 Dm7/2 G7/2", None)
    comp = [0, 1.5, 3.0, 3.5]
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"I": I, "A": A, "B": B}, "IAAB")):
        for ch, st, bt in chords:
            for c in comp:
                if st <= c + (0 if st == 0 else 0) < st + bt:
                    block(s, M.guitar, ch, bar, c if bt == 4 else st + (c % bt), 0.9, center=57, bus="gtr",
                          gain=0.55, pan=-0.3, spread=0.006)
            bassline(s, M.upright, ch, bar, st, bt, [(0, 0, 1.4), (1.5, 7, 0.4), (2, 7, 1.4), (3.5, 0, 0.4)])
        drums(s, bar, "x..x..x.x..x..x.", M.shaker, gain=0.9, pan=0.4)
        drums(s, bar, "x..x...x..x...x.", M.rim, gain=0.6, pan=-0.2)
        drums(s, bar, "x.......o.......", M.kick, gain=0.5, tone=55, punch=0.4)
        if sec != "I":
            mel_bar(s, M.mandolin, mel, bar, gain=0.75, pan=0.15)
            if bar % 8 >= 4:
                mel_bar(s, M.flute, mel, bar, gain=0.35, pan=-0.15, transpose=-12)
    mix = {"lead": dict(gain=1.0, rev=0.25), "gtr": dict(gain=1.0, rev=0.18), "bass": dict(gain=0.85, rev=0.05, lp=800),
           "drums": dict(gain=0.8, rev=0.12), "_reverb": dict(secs=1.8, predelay=0.02)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 3. Nordic Piano (felt, minimal)
def s03_nordic(out, dur):
    s = Song(80, dur, human=0.012)
    A = ("Am F C G", "E5/4 D5/2 C5/2 | C5/6 A4/2 | G5/4 E5/2 D5/2 | D5/8")
    B = ("Am F C G/2 G/2", "A5/4 G5/2 E5/2 | F5/6 E5/2 | E5/4 G5/2 C6/2 | B5/6 G5/2")
    I = ("Am F", None)
    pat = [0, 2, 3, 4, 2, 3, 4, 3]
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"I": I, "A": A, "B": B}, "IAB")):
        for ch, st, bt in chords:
            arp(s, M.piano, ch, bar, st, bt, pat, center=58, step=0.5, gain=0.75, pan=-0.1, ring=3.0, felt=True,
                vel=0.6)
            s.put("keys", M.piano(M.bass_note(ch, 2), bt * s.b, vel=0.55, felt=True), s.t(bar, st), 0.8, -0.2)
            if sec == "B":
                pad_bar(s, ch, bar, st, bt, center=55, gain=0.6, att=1.5, bright=1800)
                s.put("bass", M.cello(M.bass_note(ch, 2), bt * s.b, vel=0.7), s.t(bar, st), 0.7, human=False)
        if mel:
            mel_bar(s, M.piano, mel, bar, gain=1.0, pan=0.12, felt=True, vel=0.85)
    mix = {"lead": dict(gain=1.0, rev=0.35), "keys": dict(gain=0.9, rev=0.35), "pad": dict(gain=0.7, rev=0.5),
           "bass": dict(gain=0.7, rev=0.3), "_reverb": dict(secs=3.2, predelay=0.03, decay=2.2, damp=4500)}
    return M.render(s, out, mix, fade_in=0.05)


# ------------------------------------------------------------------ 4. Emotional piano & strings crescendo
def s04_crescendo(out, dur):
    s = Song(88, dur, human=0.01)
    A = ("Em C G D", "B4/2 E5/2 G5/2 F#5/2 | E5/4 G5/2 E5/2 | D5/2 G5/2 B5/2 A5/2 | A5/6 F#5/2")
    B = ("C G D Em", "E5/2 G5/2 C6/2 B5/2 | B5/4 D6/2 B5/2 | A5/2 D6/2 F#6/2 E6/2 | E6/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        lvl = min(1.0, 0.35 + bar / max(1, s.bars - 2))
        for ch, st, bt in chords:
            arp(s, M.piano, ch, bar, st, bt, [0, 3, 4, 5, 4, 3, 2, 3], center=57, step=0.5, gain=0.7, ring=2.4, vel=0.7)
            s.put("keys", M.piano(M.bass_note(ch, 1), bt * s.b, vel=0.7), s.t(bar, st), 0.9)
            if bar >= 3:
                pad_bar(s, ch, bar, st, bt, center=60, gain=lvl, att=1.2, bright=2400)
                s.put("bass", M.cello(M.bass_note(ch, 2), bt * s.b, vel=lvl), s.t(bar, st), 0.9, human=False)
        if bar >= 7:
            s.put("drums", M.timpani(M.bass_note(chords[0][0], 1), 0.5 * lvl), s.t(bar, 0), 0.8, human=False)
        mel_bar(s, M.piano, mel, bar, gain=1.0, pan=0.1, vel=0.9)
        if bar >= 6:
            mel_bar(s, M.violin, mel, bar, gain=0.9 * lvl, pan=-0.15, legato=1.05)
            mel_bar(s, M.violin, mel, bar, gain=0.4 * lvl, pan=0.2, transpose=-12, legato=1.05)
    mix = {"lead": dict(gain=1.0, rev=0.35), "keys": dict(gain=0.85, rev=0.3), "pad": dict(gain=0.9, rev=0.45),
           "bass": dict(gain=0.8, rev=0.3), "drums": dict(gain=0.7, rev=0.4),
           "_reverb": dict(secs=3.0, predelay=0.03, decay=2.3)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 5. Andalusia (Spanish guitar pop)
def s05_andalusia(out, dur):
    s = Song(100, dur, human=0.006)
    A = ("Am G F E", "E5/2 F5/1 E5/1 D5/2 C5/2 | D5/2 E5/1 D5/1 C5/2 B4/2 | C5/2 D5/1 C5/1 A4/2 F4/2 | G#4/4 B4/2 E5/2")
    B = ("Dm Am E Am", "F5/3 E5/1 D5/2 A5/2 | C6/4 B5/2 A5/2 | G#5/2 B5/2 D6/2 B5/2 | A5/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        for ch, st, bt in chords:
            for beat, down, v in ((0, True, 1.0), (1, False, 0.6), (1.5, True, 0.8), (2.5, False, 0.6), (3, True, 0.9), (3.5, False, 0.6)):
                if beat < bt:
                    strum(s, M.guitar, ch, bar, st + beat, down, v, center=57, gain=0.45, pan=-0.3, dur=0.9, speed=0.008)
            bassline(s, M.guitar, ch, bar, st, bt, [(0, 0, 1.5), (2, 7, 1.5)], octave=2, gain=0.8)
        drums(s, bar, "x.......x.......", M.cajon, gain=0.8)
        drums(s, bar, "....x.......x...", M.cajon, gain=0.6, slap=True)
        drums(s, bar, "..x..x..x..x..x.", M.clap, gain=0.25, pan=0.3)
        mel_bar(s, M.guitar, mel, bar, gain=1.1, pan=0.2, bright=0.7)
        if sec == "B":
            mel_bar(s, M.violin, mel, bar, gain=0.6, pan=-0.1, legato=1.05)
    mix = {"lead": dict(gain=1.0, rev=0.22), "gtr": dict(gain=0.9, rev=0.18), "bass": dict(gain=0.8, rev=0.1, lp=1200),
           "drums": dict(gain=0.75, rev=0.12), "_reverb": dict(secs=1.8)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 6. Ibiza Sunset (Balearic chill)
def s06_ibiza(out, dur):
    s = Song(110, dur, human=0.006)
    A = ("Fmaj9 Am9 Dm9 Bbmaj9", "C6/3 A5/1 G5/2 F5/2 | E5/6 r/2 | F5/2 A5/2 C6/2 D6/2 | C6/8")
    B = ("Bbmaj9 C6 Am9 Dm9", "D6/3 C6/1 A5/2 G5/2 | G5/4 E5/2 C5/2 | E5/2 G5/2 A5/2 C6/2 | A5/8")
    I = ("Fmaj9 Am9", None)
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"I": I, "A": A, "B": B}, "IAAB")):
        for ch, st, bt in chords:
            block(s, M.rhodes, ch, bar, st, 1.8, center=62, gain=0.6, pan=-0.2)
            block(s, M.rhodes, ch, bar, st + 2.5, 1.2, center=62, gain=0.45, pan=-0.2)
            pad_bar(s, ch, bar, st, bt, center=60, inst=M.pad, gain=0.8, att=0.8, bright=1300)
            arp(s, M.guitar, ch, bar, st, bt, [1, 3, 2, 4, 3, 2, 4, 5], center=64, step=0.5, bus="gtr", gain=0.35, pan=0.45, ring=1.2)
            bassline(s, M.ebass, ch, bar, st, bt, [(0, 0, 1.4), (1.5, 12, 0.4), (2.5, 7, 1.2)], gain=0.7)
        if sec != "I":
            for q in range(4):
                s.put("drums", M.kick(0.6, 54, 0.5), s.t(bar, q), 0.6, human=False)
                s.sidechain(s.t(bar, q), 0.25)
            drums(s, bar, "--x---x---x---x-", M.shaker, gain=0.8, pan=0.35)
            drums(s, bar, "....x.......x...", M.snap, gain=0.5, pan=-0.2)
            mel_bar(s, M.flute, mel, bar, gain=0.85, pan=0.1)
    mix = {"lead": dict(gain=1.0, rev=0.35), "keys": dict(gain=0.9, rev=0.25, duck=1), "pad": dict(gain=0.8, rev=0.4, duck=1),
           "gtr": dict(gain=0.8, rev=0.35), "bass": dict(gain=0.75, rev=0.05, lp=700, duck=1), "drums": dict(gain=0.7, rev=0.1),
           "_reverb": dict(secs=2.6, predelay=0.04, decay=2.6)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 7. Tropic Marimba (tropical house, soft)
def s07_tropic(out, dur):
    s = Song(100, dur, human=0.005)
    A = ("C G Am F", "E5/1 G5/1 A5/2 G5/1 E5/1 D5/2 | D5/2 B4/2 G4/4 | E5/1 G5/1 A5/2 C6/2 B5/2 | A5/4 G5/2 F5/2")
    B = ("F G Em Am", "A5/1 C6/1 A5/1 G5/1 F5/2 E5/2 | D5/2 G5/2 B5/4 | B5/1 G5/1 E5/2 D5/2 E5/2 | C5/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        for ch, st, bt in chords:
            arp(s, M.marimba, ch, bar, st, bt, [1, 2, 3, 2, 4, 3, 2, 3], center=64, step=0.5, gain=0.7, pan=-0.25)
            pad_bar(s, ch, bar, st, bt, center=60, inst=M.pad, gain=0.6, att=0.4, bright=1600)
            for q in range(4):
                s.put("bass", M.ebass(M.bass_note(ch, 2), s.b * 0.4, 0.7), s.t(bar, st + q + 0.5), 0.8)
        if bar >= 2:
            drums(s, bar, "x.......x.......", M.kick, gain=0.55, tone=56, punch=0.4)
            drums(s, bar, "....x.......x...", M.clap, gain=0.35)
            drums(s, bar, "-x-x-x-x-x-x-x-x", M.shaker, gain=0.7, pan=0.4)
        for q in (0, 2):
            s.sidechain(s.t(bar, q), 0.3)
        mel_bar(s, M.panflute, mel, bar, gain=0.9, pan=0.12)
        if sec == "B":
            mel_bar(s, M.marimba, mel, bar, gain=0.4, pan=0.3, transpose=12)
    mix = {"lead": dict(gain=1.0, rev=0.3), "keys": dict(gain=0.85, rev=0.2), "pad": dict(gain=0.6, rev=0.4, duck=1),
           "bass": dict(gain=0.7, rev=0.05, lp=600, duck=1), "drums": dict(gain=0.7, rev=0.1),
           "_reverb": dict(secs=2.2, predelay=0.03)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 8. Stockholm Folk-Pop (whistle hook)
def s08_stockholm(out, dur):
    s = Song(118, dur, human=0.006)
    A = ("Am F C G", "A4/1 C5/1 E5/1 A5/2 G5/1 E5/2 | F5/1 E5/1 C5/2 A4/4 | C5/1 E5/1 G5/1 C6/2 B5/1 G5/2 | G5/1 A5/1 B5/2 G5/4")
    B = ("F G Am Am", "A5/2 A5/1 G5/1 F5/2 E5/2 | D5/2 G5/2 B5/4 | C6/2 B5/1 A5/1 E5/2 C5/2 | A4/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        for ch, st, bt in chords:
            for beat, down, v in ((0, True, 1.0), (1, True, 0.7), (1.5, False, 0.5), (2.5, False, 0.6), (3, True, 0.8), (3.5, False, 0.5)):
                if beat < bt:
                    strum(s, lambda m, d, vel: M.guitar(m, d, vel, steel=True), ch, bar, st + beat, down, v, center=57,
                          gain=0.35, pan=-0.35, dur=0.8)
            block(s, M.piano, ch, bar, st + 0.5, 0.4, center=64, gain=0.35, pan=0.3)
            block(s, M.piano, ch, bar, st + 2.5, 0.4, center=64, gain=0.35, pan=0.3)
            bassline(s, M.ebass, ch, bar, st, bt, [(0, 0, 0.9), (1, 0, 0.9), (2, 0, 0.9), (3, 0, 0.9)], gain=0.55)
        if bar >= 2:
            drums(s, bar, "x...x...x...x...", M.kick, gain=0.45, tone=56, punch=0.4)
            drums(s, bar, "....x.......x...", M.clap, gain=0.3)
            drums(s, bar, "x-x-x-x-x-x-x-x-", M.tamb, gain=0.6, pan=0.4)
        mel_bar(s, M.whistle, mel, bar, gain=0.85, pan=0.1)
        if sec == "B":
            mel_bar(s, M.glock, mel, bar, gain=0.35, pan=-0.2, transpose=12)
    mix = {"lead": dict(gain=1.0, rev=0.28), "gtr": dict(gain=0.9, rev=0.15), "keys": dict(gain=0.7, rev=0.2),
           "bass": dict(gain=0.65, rev=0.05, lp=700), "drums": dict(gain=0.7, rev=0.08), "_reverb": dict(secs=2.0)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 9. French Touch (nu-disco, light)
def s09_frenchtouch(out, dur):
    s = Song(116, dur, human=0.004)
    A = ("Dm7 G7 Cmaj7 A7", "F5/2 E5/1 D5/1 r/2 A5/2 | G5/3 F5/1 r/2 B4/2 | E5/2 G5/1 B5/1 r/2 C6/2 | C#6/4 A5/4")
    B = ("Bbmaj7 A7 Dm7 Dm7", "D6/2 C6/1 Bb5/1 r/2 A5/2 | G5/2 E5/2 C#5/4 | F5/1 A5/1 D6/2 C6/2 A5/2 | D5/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        for ch, st, bt in chords:
            for beat in (0.5, 1.5, 2.5, 3.5):
                block(s, M.rhodes, ch, bar, st + beat, 0.35, center=64, gain=0.55, pan=-0.2)
            b = M.bass_note(ch, 2)
            for q in range(8):
                n = b + (12 if q % 2 else 0)
                s.put("bass", M.ebass(n, s.b * 0.42, 0.75 if q % 2 else 0.9), s.t(bar, st + q * 0.5), 0.75)
            if bar % 4 == 3:
                s.put("pad", M.strings(M.voicing(ch, 72), s.b * 0.5, 0.9, att=0.03, rel=0.3), s.t(bar, 3.5), 0.8, human=False)
        if bar >= 1:
            drums(s, bar, "x...x...x...x...", M.kick, gain=0.5, tone=55, punch=0.5)
            drums(s, bar, "..o...o...o...o.", M.hat, gain=0.8, open_=True, pan=0.3)
            drums(s, bar, "....x.......x...", M.clap, gain=0.35)
            for q in range(4):
                s.sidechain(s.t(bar, q), 0.3)
        mel_bar(s, M.strings, None, bar)
        if mel:
            pos = 0.0
            for m, l in M.melody(mel):
                if m is not None:
                    s.put("lead", M.strings([m, m - 12], l / 2 * s.b, 1.0, att=0.02, rel=0.25, bright=4000), s.t(bar, pos / 2), 1.0, 0.1)
                pos += l
    mix = {"lead": dict(gain=1.0, rev=0.25), "keys": dict(gain=0.85, rev=0.15, duck=1), "pad": dict(gain=0.7, rev=0.3),
           "bass": dict(gain=0.6, rev=0.03, lp=700, duck=1), "drums": dict(gain=0.7, rev=0.06), "_reverb": dict(secs=1.8)}
    return M.render(s, out, mix, master_lp=12000)


# ------------------------------------------------------------------ 10. Vienna Salon (string quartet minuet)
def s10_vienna(out, dur):
    s = Song(116, dur, beats_per_bar=3, human=0.008)
    A = ("D A7 D A G D A7 D",
         "F#5/2 A5/2 D6/2 | C#6/2 E5/2 A5/2 | D6/1 C#6/1 D6/1 E6/1 F#6/2 | E6/6 | D6/2 B5/2 G5/2 | "
         "F#5/2 A5/2 D5/2 | E5/1 F#5/1 G5/1 E5/1 C#5/2 | D5/6")
    B = ("Bm F#7 Bm A7 D G A7 D",
         "B5/2 D6/2 F#6/2 | A#5/4 C#6/2 | D6/2 C#6/2 B5/2 | A5/4 G5/2 | F#5/2 A5/2 D6/2 | B5/2 G5/2 E5/2 | "
         "C#6/1 B5/1 A5/1 G5/1 E5/2 | D5/6")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AB")):
        ch = chords[0][0]
        s.put("bass", M.cello(M.bass_note(ch, 2), s.b * 0.9, 0.9), s.t(bar, 0), 1.0, -0.35)
        v = M.voicing(ch, 62)
        for beat in (1, 2):
            s.put("comp", M.violin(v[1], s.b * 0.55, 0.55, att=0.03), s.t(bar, beat), 0.7, 0.3)   # viola part
            s.put("comp", M.violin(v[0], s.b * 0.55, 0.5, att=0.03), s.t(bar, beat), 0.6, -0.15)  # 2nd violin
        mel_bar(s, M.violin, mel, bar, gain=1.0, pan=-0.05, legato=0.95)
        if sec == "B":
            mel_bar(s, M.harp, mel, bar, gain=0.25, pan=0.25, transpose=-12)
    mix = {"lead": dict(gain=1.0, rev=0.3), "comp": dict(gain=0.85, rev=0.3), "bass": dict(gain=0.9, rev=0.25),
           "_reverb": dict(secs=2.4, predelay=0.025, decay=2.8)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 11. Baroque Garden (harpsichord & strings)
def s11_baroque(out, dur):
    s = Song(116, dur, human=0.004)
    A = ("Am Dm G C F Bdim E Am",
         "E5/1 A5/1 C6/1 B5/1 A5/1 E5/1 C5/1 E5/1 | F5/1 A5/1 D6/1 C6/1 B5/1 A5/1 F5/1 D5/1 | "
         "D5/1 G5/1 B5/1 A5/1 G5/1 D5/1 B4/1 D5/1 | E5/1 G5/1 C6/1 B5/1 C6/1 G5/1 E5/1 G5/1 | "
         "A5/1 F5/1 C6/1 A5/1 F5/1 C5/1 F5/1 A5/1 | D6/1 B5/1 F5/1 D5/1 B4/1 D5/1 F5/1 B5/1 | "
         "G#5/1 E5/1 B5/1 G#5/1 E5/1 D5/1 C5/1 B4/1 | A4/2 C5/2 E5/2 A5/2")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A}, "A")):
        ch = chords[0][0]
        arp(s, M.harpsichord, ch, bar, 0, 4, [1, 2, 3, 2], center=60, step=0.25, gain=0.35, pan=-0.3, ring=1.2)
        b = M.bass_note(ch, 2)
        for q, iv in enumerate((0, 12, 7, 12)):
            s.put("bass", M.cello(b + iv, s.b * 0.85, 0.8), s.t(bar, q), 0.8, -0.1)
        if bar >= 2:
            mel_bar(s, M.violin, mel, bar, gain=0.9, pan=0.2, legato=0.9, att=0.03)
        if bar >= 4:
            pad_bar(s, ch, bar, 0, 4, center=64, gain=0.5, att=0.3, bright=2600)
    mix = {"lead": dict(gain=1.0, rev=0.28), "keys": dict(gain=0.9, rev=0.25), "bass": dict(gain=0.85, rev=0.2),
           "pad": dict(gain=0.6, rev=0.35), "_reverb": dict(secs=2.6, predelay=0.03, decay=2.6)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 12. Grand Cinema (orchestral)
def s12_cinema(out, dur):
    s = Song(96, dur, human=0.006)
    A = ("Dm Bb F C", "A4/4 D5/2 E5/2 | F5/4 D5/4 | C5/2 F5/2 A5/2 G5/2 | G5/6 E5/2")
    B = ("Bb F C Dm", "D6/4 C6/2 Bb5/2 | A5/4 F5/4 | G5/2 A5/2 C6/2 E6/2 | D6/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        lvl = min(1.0, 0.3 + bar / max(1, s.bars - 3))
        for ch, st, bt in chords:
            b = M.bass_note(ch, 2)
            for q in range(8):
                s.put("bass", M.cello(b + (12 if q % 4 == 2 else 0), s.b * 0.45, 0.6 + 0.4 * lvl), s.t(bar, st + q * 0.5), 0.8)
            pad_bar(s, ch, bar, st, bt, center=62, gain=0.5 + 0.6 * lvl, att=0.8, bright=2200 + 1500 * lvl)
            if bar >= 4:
                s.put("brass", M.brass(M.voicing(ch, 55), bt * s.b * 0.95, 0.5 + 0.4 * lvl), s.t(bar, st), 0.7, human=False)
            block(s, M.piano, ch, bar, st, 1.0, center=60, gain=0.4)
        if bar >= 4:
            s.put("drums", M.timpani(M.bass_note(chords[0][0], 1), 0.8), s.t(bar, 0), 0.8, human=False)
            if bar % 2:
                s.put("drums", M.timpani(M.bass_note(chords[0][0], 1), 0.5), s.t(bar, 3.5), 0.6, human=False)
        mel_bar(s, M.violin, mel, bar, gain=0.7 + 0.4 * lvl, pan=0.1, legato=1.05)
        if bar >= 6:
            mel_bar(s, M.cello, mel, bar, gain=0.5, pan=-0.1, transpose=-12)
        if bar == s.bars - 2:
            s.put("fx", M.swell(s.b * 4, 1.0), s.t(bar, 0), 1.0, human=False)
    mix = {"lead": dict(gain=1.0, rev=0.38), "pad": dict(gain=0.9, rev=0.45), "bass": dict(gain=0.85, rev=0.25),
           "brass": dict(gain=0.8, rev=0.4), "keys": dict(gain=0.6, rev=0.3), "drums": dict(gain=0.75, rev=0.45),
           "fx": dict(gain=0.6, rev=0.5), "_reverb": dict(secs=3.4, predelay=0.035, decay=2.0)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 13. Manouche (gypsy jazz)
def s13_manouche(out, dur):
    s = Song(176, dur, swing=0.12, human=0.006)
    A = ("Am6 Am6 Dm6 Dm6 E7 E7 Am6 Am6",
         "E5/1 F5/1 E5/1 C5/1 A4/2 C5/2 | E5/3 D#5/1 E5/4 | F5/1 G5/1 F5/1 D5/1 B4/2 D5/2 | F5/3 E5/1 F5/4 | "
         "G#5/1 A5/1 B5/1 C6/1 D6/2 B5/2 | G#5/4 E5/4 | A5/2 C6/2 B5/1 A5/1 G#5/1 F#5/1 | A5/6 r/2")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A}, "A")):
        ch = chords[0][0]
        for beat in range(4):  # la pompe
            if beat % 2 == 0:
                s.put("bass", M.upright(M.bass_note(ch, 2) + (0 if beat == 0 else 7), s.b * 0.9), s.t(bar, beat), 0.9)
            block(s, M.guitar, ch, bar, beat, 0.25 if beat % 2 else 0.35, center=56, bus="gtr", gain=0.55 if beat % 2 else 0.4,
                  pan=-0.3, spread=0.004, bright=0.75)
        if bar >= 1:
            mel_bar(s, M.violin, mel, bar, gain=1.0, pan=0.15, legato=0.9, att=0.03)
        if bar >= 9:
            mel_bar(s, M.guitar, mel, bar, gain=0.5, pan=0.35, transpose=-12, bright=0.8)
    mix = {"lead": dict(gain=1.0, rev=0.2), "gtr": dict(gain=0.95, rev=0.12), "bass": dict(gain=0.85, rev=0.08, lp=1000),
           "_reverb": dict(secs=1.5, predelay=0.012, decay=3.8)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 14. Santorini (Greek island)
def s14_santorini(out, dur):
    s = Song(108, dur, human=0.006)
    A = ("Dm Gm A7 Dm", "A5/2 Bb5/1 A5/1 G5/2 F5/2 | G5/2 Bb5/1 A5/1 G5/4 | A5/1 Bb5/1 C#6/1 Bb5/1 A5/2 G5/2 | F5/2 E5/2 D5/4")
    B = ("Gm Dm A7 Dm", "D6/3 C6/1 Bb5/2 A5/2 | A5/2 F5/2 D5/4 | E5/1 F5/1 G5/1 A5/1 Bb5/2 C#6/2 | D6/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        for ch, st, bt in chords:
            for beat in (0, 1, 2, 3):
                if beat % 2 == 0:
                    s.put("bass", M.guitar(M.bass_note(ch, 2) + (0 if beat == 0 else 7), s.b * 0.9, 0.9), s.t(bar, st + beat), 0.8)
                else:
                    block(s, M.guitar, ch, bar, st + beat, 0.3, center=58, bus="gtr", gain=0.45, pan=-0.3, spread=0.005)
                    block(s, M.guitar, ch, bar, st + beat + 0.5, 0.25, center=58, bus="gtr", gain=0.3, pan=-0.3, spread=0.005)
        drums(s, bar, "x.....x...x.....", M.daf, gain=0.7, low=True)
        drums(s, bar, "...x.x.....x.x..", M.daf, gain=0.5, low=False, pan=0.3)
        pos = 0.0
        for m, l in M.melody(mel):
            if m is not None:
                fn = M.mandolin if l >= 2 else M.bouzouki
                s.put("lead", fn(m, l / 2 * s.b, 0.9), s.t(bar, pos / 2), 0.9 if l >= 2 else 1.0, 0.15)
            pos += l
    mix = {"lead": dict(gain=1.0, rev=0.25), "gtr": dict(gain=0.9, rev=0.15), "bass": dict(gain=0.8, rev=0.1, lp=1000),
           "drums": dict(gain=0.75, rev=0.12), "_reverb": dict(secs=1.9)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 15. Café del Mar (downtempo)
def s15_cafedelmar(out, dur):
    s = Song(90, dur, swing=0.06, human=0.008)
    A = ("Gmaj7 F#m7 Em7 A7sus4", "B5/3 A5/1 F#5/2 D5/2 | E5/6 r/2 | G5/2 B5/2 D6/2 C#6/2 | A5/8")
    B = ("Cmaj7 Bm7 Em7 A7sus4", "E6/3 D6/1 B5/2 G5/2 | A5/4 F#5/4 | G5/2 E5/2 B5/2 D6/2 | C#6/6 r/2")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AB")):
        for ch, st, bt in chords:
            block(s, M.rhodes, ch, bar, st, 1.6, center=62, gain=0.6, pan=-0.15)
            block(s, M.rhodes, ch, bar, st + 2.5, 1.0, center=62, gain=0.4, pan=-0.15)
            pad_bar(s, ch, bar, st, bt, center=58, inst=M.pad, gain=0.7, att=1.2, bright=1100)
            arp(s, M.guitar, ch, bar, st, bt, [None, 2, 3, None, 4, 3, None, 2], center=64, step=0.5, bus="gtr", gain=0.35, pan=0.45)
            bassline(s, M.ebass, ch, bar, st, bt, [(0, 0, 1.4), (2.5, 7, 0.9), (3.5, 12, 0.4)], gain=0.65)
        if bar >= 1:
            drums(s, bar, "x.......-.x.....", M.kick, gain=0.5, tone=52, punch=0.3)
            drums(s, bar, "....x.......x...", M.rim, gain=0.7, pan=-0.1)
            drums(s, bar, "x-x-x-x-x-x-x-x-", M.shaker, gain=0.6, pan=0.35)
        mel_bar(s, M.flute, mel, bar, gain=0.85, pan=0.1)
        if sec == "B":
            mel_bar(s, M.vibes, mel, bar, gain=0.35, pan=-0.3)
    mix = {"lead": dict(gain=1.0, rev=0.35), "keys": dict(gain=0.9, rev=0.25), "pad": dict(gain=0.7, rev=0.45),
           "gtr": dict(gain=0.8, rev=0.35), "bass": dict(gain=0.7, rev=0.05, lp=650), "drums": dict(gain=0.75, rev=0.1),
           "_reverb": dict(secs=2.8, predelay=0.04, decay=2.4)}
    return M.render(s, out, mix, master_lp=11000)


# ------------------------------------------------------------------ 16. Melodic House (soft, no heavy kick)
def s16_melodic(out, dur):
    s = Song(120, dur, human=0.003)
    A = ("Dm Bb F C", None)
    seq = [0, 3, 5, 3, 6, 3, 5, 4, 0, 3, 5, 3, 6, 5, 4, 3]
    hook = "D6/3 C6/1 A5/2 F5/2 | F5/3 E5/1 D5/4 | C6/3 A5/1 F5/2 C5/2 | E5/3 F5/1 G5/4"
    hb = [h.strip() for h in hook.split("|")]
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A}, "A")):
        ch = chords[0][0]
        arp(s, M.vibes, ch, bar, 0, 4, seq, center=64, step=0.25, gain=0.45, pan=-0.3, ring=1.0)
        arp(s, M.vibes, ch, bar, 0.75, 3.25, seq[::-1], center=64, step=0.25, gain=0.2, pan=0.4, ring=1.0)  # echo
        pad_bar(s, ch, bar, 0, 4, center=60, inst=M.pad, gain=0.9, att=0.6, bright=1400 + 120 * bar)
        bassline(s, M.subbass, ch, bar, 0, 4, [(0, 0, 0.9), (1.5, 0, 0.4), (2, 0, 0.9), (3.5, 12, 0.4)], gain=0.6)
        if bar >= 4:
            drums(s, bar, "x...x...x...x...", M.kick, gain=0.45, tone=55, punch=0.35)
            drums(s, bar, "..x...x...x...x.", M.hat, gain=0.6, pan=0.3)
            drums(s, bar, "....x.......x...", M.snap, gain=0.4)
            for q in range(4):
                s.sidechain(s.t(bar, q), 0.35)
        if bar >= 4:
            mel_bar(s, M.panflute, hb[bar % 4], bar, gain=0.85, pan=0.1)
    mix = {"lead": dict(gain=1.0, rev=0.35), "keys": dict(gain=0.85, rev=0.3, duck=1), "pad": dict(gain=0.8, rev=0.4, duck=1),
           "bass": dict(gain=0.65, rev=0.02, lp=300, duck=1), "drums": dict(gain=0.7, rev=0.08),
           "_reverb": dict(secs=2.6, predelay=0.04)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 17. Music Box Dreams (celesta waltz)
def s17_musicbox(out, dur):
    s = Song(96, dur, beats_per_bar=3, human=0.006)
    A = ("C Am F G C Am Dm G", "E6/2 G6/2 E6/2 | C6/4 A5/2 | F6/2 E6/2 D6/2 | D6/6 | E6/2 G6/2 C7/2 | A6/4 E6/2 | F6/2 A6/2 F6/2 | G6/6")
    B = ("F G Em Am Dm G C C", "A6/2 G6/2 F6/2 | B6/2 A6/2 G6/2 | G6/2 E6/2 B5/2 | C6/4 E6/2 | F6/2 E6/2 D6/2 | B5/4 D6/2 | C6/6 | r/6")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AB")):
        ch = chords[0][0]
        s.put("bass", M.harp(M.bass_note(ch, 2), s.b * 2.5, 0.8), s.t(bar, 0), 0.9, -0.2)
        arp(s, M.harp, ch, bar, 1, 2, [1, 2, 3, 2], center=60, step=0.5, gain=0.5, pan=-0.15)
        pad_bar(s, ch, bar, 0, 3, center=64, gain=0.5, att=0.8, bright=1800)
        mel_bar(s, M.musicbox, mel, bar, gain=1.0, pan=0.15)
        mel_bar(s, M.celesta, mel, bar, gain=0.5, pan=-0.1, transpose=-12)
    mix = {"lead": dict(gain=1.0, rev=0.4), "keys": dict(gain=0.85, rev=0.35), "bass": dict(gain=0.8, rev=0.3),
           "pad": dict(gain=0.6, rev=0.5), "_reverb": dict(secs=3.2, predelay=0.03, decay=2.2)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 18. Happy Ukulele
def s18_ukulele(out, dur):
    s = Song(116, dur, human=0.006)
    A = ("F C Dm Bb", "A5/1 C6/1 A5/1 G5/1 F5/2 C5/2 | E5/2 G5/2 C6/4 | D6/1 C6/1 A5/1 F5/1 D5/2 F5/2 | D5/2 F5/2 G5/4")
    B = ("Bb C Am Dm Bb C F F", "D6/2 D6/1 C6/1 Bb5/4 | C6/2 E6/2 G5/4 | A5/1 C6/1 E6/2 C6/2 A5/2 | F5/8 | "
         "D6/2 C6/2 Bb5/2 A5/2 | G5/2 A5/2 Bb5/2 C6/2 | A5/8 | r/8")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AAB")):
        for ch, st, bt in chords:
            for beat, down, v in ((0, True, 1.0), (1, True, 0.6), (1.5, False, 0.6), (2.5, False, 0.7), (3, True, 0.8), (3.5, False, 0.5)):
                if beat < bt:
                    strum(s, M.ukulele, ch, bar, st + beat, down, v, center=67, gain=0.4, pan=-0.3, dur=0.6, speed=0.007)
            bassline(s, M.upright, ch, bar, st, bt, [(0, 0, 0.9), (2, 7, 0.9)], gain=0.7)
        drums(s, bar, "x.......x.......", M.kick, gain=0.4, tone=58, punch=0.3)
        drums(s, bar, "....x.......x...", M.clap, gain=0.3)
        drums(s, bar, "..x...x...x...x.", M.snap, gain=0.45, pan=0.3)
        mel_bar(s, M.glock, mel, bar, gain=0.85, pan=0.15)
        if sec == "B":
            mel_bar(s, M.whistle, mel, bar, gain=0.5, pan=-0.15, transpose=-12)
    mix = {"lead": dict(gain=1.0, rev=0.25), "gtr": dict(gain=0.9, rev=0.15), "bass": dict(gain=0.75, rev=0.05, lp=900),
           "drums": dict(gain=0.7, rev=0.08), "_reverb": dict(secs=1.8)}
    return M.render(s, out, mix)


# ------------------------------------------------------------------ 19. Neo-Soul Lounge
def s19_neosoul(out, dur):
    s = Song(82, dur, swing=0.1, human=0.01)
    A = ("Fmaj9 Em7 Dm9 G13", "A5/3 G5/1 E5/2 C5/2 | D5/4 r/2 B4/2 | C5/1 D5/1 F5/2 A5/2 C6/2 | B5/6 r/2")
    B = ("Bbmaj9 A7 Dm9 G13", "D6/3 C6/1 A5/2 F5/2 | E5/2 C#5/2 G5/4 | F5/2 A5/2 C6/2 E6/2 | D6/6 r/2")
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"A": A, "B": B}, "AB")):
        for ch, st, bt in chords:
            block(s, M.rhodes, ch, bar, st, 1.4, center=62, gain=0.65, pan=-0.15, spread=0.012)
            block(s, M.rhodes, ch, bar, st + 1.75, 0.6, center=62, gain=0.45, pan=-0.15, spread=0.01)
            block(s, M.rhodes, ch, bar, st + 3.0, 0.9, center=62, gain=0.5, pan=-0.15, spread=0.012)
            bassline(s, M.upright, ch, bar, st, bt, [(0, 0, 1.4), (1.75, 7, 0.4), (2.5, 10, 0.4), (3, 12, 0.9)], gain=0.85)
        drums(s, bar, "x......x..x.....", M.kick, gain=0.5, tone=52, punch=0.3)
        drums(s, bar, "....x.......x...", M.rim, gain=0.8)
        drums(s, bar, "x.x.x.x.x.x.x.x.", M.brush, gain=0.7, pan=0.3)
        mel_bar(s, M.vibes, mel, bar, gain=0.95, pan=0.15)
    mix = {"lead": dict(gain=1.0, rev=0.3), "keys": dict(gain=0.9, rev=0.22), "bass": dict(gain=0.85, rev=0.05, lp=900),
           "drums": dict(gain=0.75, rev=0.1), "_reverb": dict(secs=2.2, predelay=0.025)}
    return M.render(s, out, mix, master_lp=12000)


# ------------------------------------------------------------------ 20. Baku Breeze (Azerbaijani-European fusion)
def s20_baku(out, dur):
    s = Song(96, dur, human=0.008)
    # D minor with Bayati-like flavour (Eb), tar melody with grace slides over piano & strings
    A = ("Dm Gm C Dm", "A5/2 Bb5/1 A5/1 G5/2 F5/2 | G5/1 A5/1 Bb5/2 A5/4 | G5/2 E5/1 F5/1 G5/2 C6/2 | A5/6 r/2")
    B = ("Bb F Gm A7", "D6/2 Eb6/1 D6/1 C6/2 Bb5/2 | A5/2 C6/2 F5/4 | G5/1 A5/1 Bb5/1 C6/1 D6/2 Bb5/2 | A5/2 G5/1 F5/1 E5/2 C#5/2")
    I = ("Dm Dm", None)
    for bar, (sec, chords, mel, k) in enumerate(section_plan(s, {"I": I, "A": A, "B": B}, "IAAB")):
        for ch, st, bt in chords:
            arp(s, M.piano, ch, bar, st, bt, [0, 2, 3, 4, 3, 2, 4, 3], center=57, step=0.5, gain=0.55, pan=-0.2, ring=2.0, vel=0.65)
            pad_bar(s, ch, bar, st, bt, center=62, gain=0.65, att=0.9, bright=2000)
            s.put("bass", M.cello(M.bass_note(ch, 2), bt * s.b, 0.8), s.t(bar, st), 0.8, human=False)
        if sec != "I":
            drums(s, bar, "x.....x...x.....", M.daf, gain=0.6, low=True)
            drums(s, bar, "...x.....x...x.x", M.daf, gain=0.4, low=False, pan=0.3)
        else:
            # free intro phrase (mugham-style), long notes with slides
            for j, (m, at, ln) in enumerate(((M.midi("A5"), 0.0, 1.5), (M.midi("Bb5"), 1.5, 0.5), (M.midi("A5"), 2.0, 2.0))):
                s.put("lead", M.tar(m, ln * s.b, 0.9, slide_from=m - 2 if j == 0 else None), s.t(bar, at), 0.9, 0.1)
        if mel:
            pos = 0.0
            for m, l in M.melody(mel):
                if m is not None:
                    s.put("lead", M.tar(m, l / 2 * s.b, 0.95, slide_from=(m - 1 if l >= 2 else None)), s.t(bar, pos / 2), 1.0, 0.1)
                pos += l
            if sec == "B":
                mel_bar(s, M.violin, mel, bar, gain=0.5, pan=-0.2, legato=1.05)
    mix = {"lead": dict(gain=1.0, rev=0.3), "keys": dict(gain=0.85, rev=0.3), "pad": dict(gain=0.7, rev=0.45),
           "bass": dict(gain=0.75, rev=0.25), "drums": dict(gain=0.75, rev=0.15), "_reverb": dict(secs=2.8, predelay=0.03, decay=2.4)}
    return M.render(s, out, mix)


SONGS = [
    ("01-paris-kafe", "Paris kafesi", "Fransız akkordeon valsı", s01_paris),
    ("02-riviera", "Riviera", "İtalyan bossa · mandolina", s02_riviera),
    ("03-skandinav-piano", "Skandinav pianosu", "Sakit · minimal · lüks", s03_nordic),
    ("04-piano-simli", "Piano və simlilər", "Emosional crescendo", s04_crescendo),
    ("05-andalusiya", "Andalusiya", "İspan gitarası · kaxon", s05_andalusia),
    ("06-ibiza-gun-batimi", "İbiza gün batımı", "Balear chill · fleyta", s06_ibiza),
    ("07-tropik-marimba", "Tropik marimba", "Yay · pan-fleyta", s07_tropic),
    ("08-stokholm-pop", "Stokholm pop", "Fit melodiyası · gitara", s08_stockholm),
    ("09-fransiz-disko", "Fransız diskosu", "Yüngül nu-disco", s09_frenchtouch),
    ("10-vyana-salonu", "Vyana salonu", "Simli kvartet · menuet", s10_vienna),
    ("11-barokko-bagi", "Barokko bağı", "Klavesin · skripka", s11_baroque),
    ("12-boyuk-kino", "Böyük kino", "Orkestr · epik", s12_cinema),
    ("13-manus-caz", "Manuş caz", "Qaraçı cazı · skripka", s13_manouche),
    ("14-santorini", "Santorini", "Yunan adası · buzuki", s14_santorini),
    ("15-kafe-del-mar", "Café del Mar", "Downtempo · Rhodes", s15_cafedelmar),
    ("16-melodik-haus", "Melodik haus", "Yumşaq · axıcı", s16_melodic),
    ("17-musiqi-qutusu", "Musiqi qutusu", "Xəyal · çelesta valsı", s17_musicbox),
    ("18-sen-ukulele", "Şən ukulele", "Pozitiv · qlokenşpil", s18_ukulele),
    ("19-neo-soul", "Neo-soul lounge", "Rhodes · vibrafon", s19_neosoul),
    ("20-baki-mehi", "Bakı mehi", "Tar · piano · simlilər", s20_baku),
]
KEYS = {name.split("-", 1)[0]: fn for name, _, _, fn in SONGS}  # "01".."20"

if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 32.0
    only = sys.argv[3:]
    for name, _, _, fn in SONGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        fn(out / f"{name}.mp3", dur)
        print("ok", name, flush=True)
