#!/usr/bin/env python3
"""Parse a chord progression file and generate a MIDI file."""

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

    # Determine quality and collect modifiers
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

    # Normalize for easier matching
    rest = rest.lower().strip()

    # Check for "minor" / "min" / "m" (but not "major" or "maj")
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
        is_major7 = True  # "major" before a 7/9 means major-7 quality
        rest = re.sub(r'^(major|maj)\s*', '', rest)
    # plain "m" at start (not followed by 'a' for major)
    elif re.match(r'm(?!a)', rest):
        is_minor = True
        rest = re.sub(r'^m\s*', '', rest)

    # Parse remaining tokens for extensions
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
            # skip unknown token character
            rest = rest[1:]

    # Build intervals from root
    intervals = []

    # Third (or sus4)
    if is_sus:
        intervals.append(5)   # perfect 4th
    elif is_minor or is_dim:
        intervals.append(3)   # minor 3rd
    else:
        intervals.append(4)   # major 3rd

    # Fifth
    if is_dim:
        intervals.append(6)   # diminished 5th
    elif is_aug or sharp_5:
        intervals.append(8)   # augmented 5th
    else:
        intervals.append(7)   # perfect 5th

    # Sixth
    if has_6:
        intervals.append(9)

    # Seventh
    if has_7 or has_9 or has_11:
        if is_dim:
            intervals.append(9)   # diminished 7th
        elif is_major7:
            intervals.append(11)  # major 7th
        else:
            intervals.append(10)  # dominant (minor) 7th

    # Ninth
    if has_9:
        if sharp_9:
            intervals.append(15)  # #9 (minor 3rd + octave)
        else:
            intervals.append(14)  # major 9th

    # Eleventh
    if has_11:
        if sharp_11:
            intervals.append(18)  # #11 (tritone + octave)
        else:
            intervals.append(17)  # perfect 11th

    # Root + intervals, voiced around C3-C5 range
    base = 48 + root  # root in octave 3
    if base < 48:
        base += 12

    notes = [base] + [base + i for i in intervals]
    return notes


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'moolight.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'moolight.mid'

    # Parse input
    chords = []
    with open(input_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Split on last colon to get chord name and beats
            parts = line.rsplit(':', 1)
            if len(parts) != 2:
                print(f"Skipping malformed line: {line}")
                continue
            chord_name = parts[0].strip()
            beats = int(parts[1].strip())
            chords.append((chord_name, beats))

    # Create MIDI
    tempo = 120  # BPM
    midi = MIDIFile(1)
    track = 0
    channel = 0
    volume = 80
    time = 0  # in beats

    midi.addTempo(track, 0, tempo)
    midi.addProgramChange(track, channel, 0, 0)  # acoustic grand piano

    for chord_name, beats in chords:
        try:
            notes = parse_chord(chord_name)
        except ValueError as e:
            print(f"Warning: {e}, skipping")
            time += beats
            continue

        for note in notes:
            midi.addNote(track, channel, note, time, beats, volume)

        print(f"Beat {time:3d}: {chord_name:25s} -> MIDI notes {notes}  ({beats} beats)")
        time += beats

    with open(output_file, 'wb') as f:
        midi.writeFile(f)

    print(f"\nWrote {output_file} ({time} total beats at {tempo} BPM)")


if __name__ == '__main__':
    main()
