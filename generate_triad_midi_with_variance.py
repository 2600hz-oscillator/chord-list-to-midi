#!/usr/bin/env python3
"""Parse a chord progression file and generate a humanized 3-track MIDI file.

For each chord, only the 3 most dominant notes are kept (root, third, color
note) and placed on separate tracks for monophonic synths.

Simulates a keyboard player by:
- Slight asynchrony between voices (not strummed — just imprecise simultaneity)
- Per-voice velocity that's relatively uniform (no guitarist-style root accent)
- Legato overlap: notes often sustain slightly into the next chord (sustain pedal)
- Occasional early attacks: inner voices sometimes anticipate the beat
- Subtle phrase-level dynamics (crescendo / decrescendo over groups of chords)
"""

import re
import sys
import random
import math
from midiutil import MIDIFile

# ---------- note / chord mappings ----------

NOTE_MAP = {
    'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11
}

SEED = 42


def parse_root(token):
    """Return (semitone 0-11, remaining string) from the start of token."""
    token = token.strip().lower()
    m = re.match(r'^([a-g])\s*(sharp|flat|#|b)?', token)
    if not m:
        raise ValueError(f"Can't parse root from: {token}")
    note = NOTE_MAP[m.group(1)]
    acc = m.group(2)
    if acc in ('sharp', '#'):
        note = (note + 1) % 12
    elif acc in ('flat', 'b'):
        note = (note - 1) % 12
    rest = token[m.end():].strip()
    return note, rest


def parse_chord(name):
    """Return a list of MIDI note numbers (rooted around middle-C octave) for a chord name."""
    root, rest = parse_root(name)

    is_minor = False
    is_dim = False
    is_aug = False
    is_major7 = False
    is_sus = False
    has_6 = False
    has_7 = False
    has_9 = False
    has_11 = False
    sharp_9 = False
    sharp_5 = False
    sharp_11 = False

    rest = rest.lower().strip()

    if re.match(r'minor|min(?!or)', rest):
        is_minor = True
        rest = re.sub(r'^(minor|min)\s*', '', rest)
    elif re.match(r'dim', rest):
        is_dim = True
        rest = re.sub(r'^dim(inished)?\s*', '', rest)
    elif re.match(r'aug', rest):
        is_aug = True
        rest = re.sub(r'^aug(mented)?\s*', '', rest)
    elif re.match(r'major|maj', rest):
        is_major7 = True
        rest = re.sub(r'^(major|maj)\s*', '', rest)
    elif re.match(r'm(?!a)', rest):
        is_minor = True
        rest = re.sub(r'^m\s*', '', rest)

    while rest:
        rest = rest.strip()
        if not rest:
            break
        if re.match(r'sus', rest):
            is_sus = True
            rest = re.sub(r'^sus\d?\s*', '', rest)
        elif re.match(r'sharp\s*11|#11', rest):
            sharp_11 = True
            has_11 = True
            rest = re.sub(r'^(sharp\s*11|#11)\s*', '', rest)
        elif re.match(r'sharp\s*9|#9', rest):
            sharp_9 = True
            has_9 = True
            rest = re.sub(r'^(sharp\s*9|#9)\s*', '', rest)
        elif re.match(r'sharp\s*5|#5', rest):
            sharp_5 = True
            rest = re.sub(r'^(sharp\s*5|#5)\s*', '', rest)
        elif re.match(r'11', rest):
            has_11 = True
            has_9 = True
            has_7 = True
            rest = re.sub(r'^11\s*', '', rest)
        elif re.match(r'9', rest):
            has_9 = True
            has_7 = True
            rest = re.sub(r'^9\s*', '', rest)
        elif re.match(r'7', rest):
            has_7 = True
            rest = re.sub(r'^7\s*', '', rest)
        elif re.match(r'6', rest):
            has_6 = True
            rest = re.sub(r'^6\s*', '', rest)
        else:
            rest = rest[1:]

    labeled = []

    if is_sus:
        labeled.append((5, 1))
    elif is_minor or is_dim:
        labeled.append((3, 1))
    else:
        labeled.append((4, 1))

    if is_dim:
        labeled.append((6, 5))
    elif is_aug or sharp_5:
        labeled.append((8, 5))
    else:
        labeled.append((7, 5))

    if has_6:
        labeled.append((9, 4))

    if has_7 or has_9 or has_11:
        if is_dim:
            labeled.append((9, 2))
        elif is_major7:
            labeled.append((11, 2))
        else:
            labeled.append((10, 2))

    if has_9:
        if sharp_9:
            labeled.append((15, 3))
        else:
            labeled.append((14, 3))

    if has_11:
        if sharp_11:
            labeled.append((18, 3))
        else:
            labeled.append((17, 3))

    base = 48 + root
    if base < 48:
        base += 12

    labeled.sort(key=lambda x: x[1])
    picked = labeled[:2]

    notes = [base] + [base + iv for iv, _ in picked]
    notes.sort()
    return notes


def humanize_keyboard(midi, notes, start_time, duration, chord_index, total_chords, rng):
    """Add 3 notes across 3 tracks with keyboard-style humanization."""

    # --- Phrase-level dynamics (slow sine wave over the progression) ---
    # Creates natural crescendo/decrescendo over ~8 chord groups
    phrase_pos = chord_index / max(total_chords - 1, 1)
    phrase_curve = math.sin(phrase_pos * math.pi * 2.5)  # ~2.5 cycles across piece
    base_velocity = 74 + int(phrase_curve * 8)  # range roughly 66-82

    for i, note in enumerate(notes):
        track = i
        channel = i

        # --- Timing: slight asynchrony between voices ---
        # Keyboard players don't strum — they just aren't perfectly synchronized.
        # Each voice gets an independent small offset.
        onset_offset = rng.gauss(0, 0.012)

        # ~15% chance an inner voice (track 1) anticipates the beat slightly
        if i == 1 and rng.random() < 0.15:
            onset_offset -= rng.uniform(0.03, 0.08)

        note_start = max(0.0, start_time + onset_offset)

        # --- Velocity: relatively uniform across voices ---
        # Keyboard players balance voices more evenly than guitarists.
        # Small per-note jitter, no systematic accent on root.
        vel = base_velocity + rng.randint(-4, 4)

        # Occasionally the top voice gets a slight melodic accent
        if i == 2 and rng.random() < 0.25:
            vel += rng.randint(3, 7)

        vel = max(45, min(120, vel))

        # --- Duration: legato overlap (sustain pedal effect) ---
        # Most notes sustain slightly past the chord boundary.
        # ~60% of the time: slight overlap into next chord (pedal sustain)
        # ~25%: release right at the boundary
        # ~15%: early release (lifting before next chord)
        roll = rng.random()
        if roll < 0.60:
            # Legato overlap — hold 0.05 to 0.25 beats into next chord
            note_dur = duration + rng.uniform(0.05, 0.25)
        elif roll < 0.85:
            # Clean release at boundary with tiny variance
            note_dur = duration + rng.uniform(-0.03, 0.03)
        else:
            # Early release
            note_dur = duration - rng.uniform(0.05, 0.20)

        # Compensate for onset offset so duration stays musically correct
        note_dur -= onset_offset
        note_dur = max(0.15, note_dur)

        midi.addNote(track, channel, note, note_start, note_dur, vel)

    return base_velocity


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'moolight.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'moolight_triad_with_variance.mid'

    rng = random.Random(SEED)

    # Parse input
    chords = []
    with open(input_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.rsplit(':', 1)
            if len(parts) != 2:
                print(f"Skipping malformed line: {line}")
                continue
            chord_name = parts[0].strip()
            beats = int(parts[1].strip())
            chords.append((chord_name, beats))

    # Create MIDI — 3 tracks, one voice per track
    tempo = 120
    midi = MIDIFile(3)

    track_names = ['Low', 'Mid', 'High']
    for t in range(3):
        midi.addTempo(t, 0, tempo)
        midi.addTrackName(t, 0, track_names[t])
        midi.addProgramChange(t, t, 0, 0)  # acoustic grand piano

    time = 0.0
    total_chords = len(chords)

    for idx, (chord_name, beats) in enumerate(chords):
        try:
            notes = parse_chord(chord_name)
        except ValueError as e:
            print(f"Warning: {e}, skipping")
            time += beats
            continue

        vel = humanize_keyboard(midi, notes, time, beats, idx, total_chords, rng)
        print(f"Beat {time:6.2f}: {chord_name:25s} -> {list(zip(track_names, notes))}  ({beats} beats, vel~{vel})")
        time += beats

    with open(output_file, 'wb') as f:
        midi.writeFile(f)

    print(f"\nWrote {output_file} ({time:.0f} total beats at {tempo} BPM)")
    print("3 tracks: Low / Mid / High — keyboard-style humanization")
    print("Humanization: voice asynchrony, phrase dynamics, legato overlap, anticipation")


if __name__ == '__main__':
    main()
