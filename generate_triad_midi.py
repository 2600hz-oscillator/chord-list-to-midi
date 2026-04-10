#!/usr/bin/env python3
"""Parse a chord progression file and generate a 3-track MIDI file.

For each chord, only the 3 most dominant notes are kept:
  1. Root
  2. Third (or sus4) — defines the chord quality
  3. Most colorful remaining note (7th > extensions > 6th > 5th)

Each note is placed on its own MIDI track so the file can drive
three independent monophonic synthesizers.
"""

import re
import sys
from midiutil import MIDIFile

# ---------- note / chord mappings ----------

NOTE_MAP = {
    'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11
}


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

    # Build intervals list with labels for priority selection
    # Each entry: (interval_semitones, priority)
    # Lower priority number = more important = picked first
    # Priority: root=0, third=1, 7th=2, extensions=3, 6th=4, 5th=5
    labeled = []

    # Third (or sus4)
    if is_sus:
        labeled.append((5, 1))    # sus4
    elif is_minor or is_dim:
        labeled.append((3, 1))    # minor 3rd
    else:
        labeled.append((4, 1))    # major 3rd

    # Fifth
    if is_dim:
        labeled.append((6, 5))
    elif is_aug or sharp_5:
        labeled.append((8, 5))
    else:
        labeled.append((7, 5))

    # Sixth
    if has_6:
        labeled.append((9, 4))

    # Seventh
    if has_7 or has_9 or has_11:
        if is_dim:
            labeled.append((9, 2))
        elif is_major7:
            labeled.append((11, 2))
        else:
            labeled.append((10, 2))

    # Ninth
    if has_9:
        if sharp_9:
            labeled.append((15, 3))
        else:
            labeled.append((14, 3))

    # Eleventh
    if has_11:
        if sharp_11:
            labeled.append((18, 3))
        else:
            labeled.append((17, 3))

    base = 48 + root
    if base < 48:
        base += 12

    # Root is always included (priority 0)
    # Pick the 2 most important remaining notes by priority (lower = more important)
    labeled.sort(key=lambda x: x[1])
    picked = labeled[:2]

    notes = [base] + [base + iv for iv, _ in picked]
    # Sort by pitch for consistent track assignment (low, mid, high)
    notes.sort()
    return notes


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'moolight.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'moolight_triad.mid'

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

    # Create MIDI — 3 tracks, one note per track
    tempo = 120
    midi = MIDIFile(3)
    volume = 80
    time = 0

    track_names = ['Low', 'Mid', 'High']
    for t in range(3):
        midi.addTempo(t, 0, tempo)
        midi.addTrackName(t, 0, track_names[t])
        midi.addProgramChange(t, t, 0, 0)  # acoustic grand piano

    for chord_name, beats in chords:
        try:
            notes = parse_chord(chord_name)
        except ValueError as e:
            print(f"Warning: {e}, skipping")
            time += beats
            continue

        for i, note in enumerate(notes):
            midi.addNote(i, i, note, time, beats, volume)

        print(f"Beat {time:3d}: {chord_name:25s} -> tracks {list(zip(track_names, notes))}  ({beats} beats)")
        time += beats

    with open(output_file, 'wb') as f:
        midi.writeFile(f)

    print(f"\nWrote {output_file} ({time} total beats at {tempo} BPM)")
    print("3 tracks: Low / Mid / High — one monophonic voice per track")


if __name__ == '__main__':
    main()
