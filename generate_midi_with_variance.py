#!/usr/bin/env python3
"""Parse a chord progression file and generate a humanized MIDI file.

Simulates a human guitarist by:
- Staggering note onsets within a chord (strumming effect)
- Varying velocity per note
- Occasionally letting a note or two ring over into the next chord
- Adding slight timing drift to chord start times
"""

import re
import sys
import random
from midiutil import MIDIFile

# ---------- note / chord mappings ----------

NOTE_MAP = {
    'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11
}

SEED = 42  # reproducible but natural-sounding


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

    intervals = []

    if is_sus:
        intervals.append(5)
    elif is_minor or is_dim:
        intervals.append(3)
    else:
        intervals.append(4)

    if is_dim:
        intervals.append(6)
    elif is_aug or sharp_5:
        intervals.append(8)
    else:
        intervals.append(7)

    if has_6:
        intervals.append(9)

    if has_7 or has_9 or has_11:
        if is_dim:
            intervals.append(9)
        elif is_major7:
            intervals.append(11)
        else:
            intervals.append(10)

    if has_9:
        if sharp_9:
            intervals.append(15)
        else:
            intervals.append(14)

    if has_11:
        if sharp_11:
            intervals.append(18)
        else:
            intervals.append(17)

    base = 48 + root
    if base < 48:
        base += 12

    notes = [base] + [base + i for i in intervals]
    return notes


def humanize_chord(midi, track, channel, notes, start_time, duration, rng):
    """Add a chord with human-like strum, velocity variation, and occasional ring-out."""

    num_notes = len(notes)

    # --- Strum: stagger notes from low to high (like a downstroke) ---
    # Total strum spread: 0.02 to 0.08 beats (subtle but audible)
    strum_spread = rng.uniform(0.02, 0.08)
    strum_delays = [i * (strum_spread / max(num_notes - 1, 1)) for i in range(num_notes)]

    # Occasionally strum upward (high to low) ~20% of the time
    if rng.random() < 0.20:
        strum_delays = strum_delays[::-1]

    # --- Slight global timing drift (push/pull feel) ---
    drift = rng.gauss(0, 0.015)  # subtle: std dev of 15ms worth of beats at 120bpm

    # --- Velocity variation ---
    base_velocity = rng.randint(72, 88)

    # --- Ring-out: ~30% chance that 1-2 notes extend past the chord duration ---
    ring_notes = set()
    if rng.random() < 0.30:
        num_ring = rng.randint(1, min(2, num_notes))
        # Prefer upper notes to ring out (more natural for guitar)
        ring_candidates = list(range(num_notes))
        ring_notes = set(rng.sample(ring_candidates[-3:] if num_notes > 3 else ring_candidates, num_ring))

    for i, note in enumerate(notes):
        note_start = start_time + drift + strum_delays[i]
        # Ensure note_start doesn't go negative
        note_start = max(0.0, note_start)

        # Velocity: root and 5th slightly louder, upper extensions softer
        if i == 0:
            vel = base_velocity + rng.randint(3, 8)   # root accented
        elif i <= 2:
            vel = base_velocity + rng.randint(-2, 4)
        else:
            vel = base_velocity + rng.randint(-6, 0)   # extensions softer

        vel = max(40, min(127, vel))

        # Duration: normal notes get slight variation; ring-out notes extend
        if i in ring_notes:
            # Ring 0.3–0.7 beats into the next chord
            note_dur = duration + rng.uniform(0.3, 0.7)
        else:
            # Slight duration variance: most notes slightly shorter than full beat
            # (guitarist fingers lift just before next chord)
            note_dur = duration - rng.uniform(0.02, 0.12) - strum_delays[i]
            note_dur = max(0.1, note_dur)

        midi.addNote(track, channel, note, note_start, note_dur, vel)

    return base_velocity


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'moolight.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'moolight_with_variance.mid'

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

    # Create MIDI
    tempo = 120
    midi = MIDIFile(1)
    track = 0
    channel = 0
    time = 0.0

    midi.addTempo(track, 0, tempo)
    midi.addProgramChange(track, channel, 0, 25)  # nylon string guitar

    for chord_name, beats in chords:
        try:
            notes = parse_chord(chord_name)
        except ValueError as e:
            print(f"Warning: {e}, skipping")
            time += beats
            continue

        vel = humanize_chord(midi, track, channel, notes, time, beats, rng)
        print(f"Beat {time:6.2f}: {chord_name:25s} -> {notes}  ({beats} beats, vel~{vel})")
        time += beats

    with open(output_file, 'wb') as f:
        midi.writeFile(f)

    print(f"\nWrote {output_file} ({time:.0f} total beats at {tempo} BPM)")
    print("Humanization: strum stagger, velocity variation, occasional ring-out, timing drift")


if __name__ == '__main__':
    main()
