# NOTE: MADE 100% WITH CLAUDE OPUS. IF YOU DISLIKE THIS THAT'S FINE YOU PROBABLY DON'T NEED IT (and maybe you are smort enough to do MIDI transcription without robots. I'm not!)

# Chord Tool

Generate MIDI files from a simple text-based chord progression format.

## Input Format

A plain text file where each line is a chord name followed by a colon and a beat count:

```
c6:2
a minor 7:2
d minor 7:2
d flat 7 sharp 9:2
```

Chords are played top to bottom in the order they appear. The number after the colon is how many beats to hold the chord.

### Supported chord syntax

- **Root notes:** `a` through `g`, with optional `sharp` or `flat` (e.g., `f sharp`, `d flat`, `b`)
- **Qualities:** `minor` / `dim` / `aug` / `major` (defaults to major if omitted)
- **Extensions:** `6`, `7`, `9`, `11`
- **Modifiers:** `sharp 5`, `sharp 9`, `sharp 11`, `sus`

These can be combined freely, e.g., `d flat 7 sharp 9`, `f sharp minor 11`, `g 7 sus`.

## Scripts

### `generate_midi.py`

Produces a clean, quantized MIDI file. Every note in a chord starts at exactly the same time with uniform velocity.

```sh
python3 generate_midi.py input.txt output.mid
```

Defaults to `moolight.txt` / `moolight.mid` if no arguments are given.

### `generate_midi_with_variance.py`

Produces a humanized MIDI file that simulates a guitarist playing the chords. The humanization includes:

- **Strum stagger** — notes within each chord start slightly apart (low-to-high for downstrokes, occasionally reversed for upstrokes)
- **Timing drift** — each chord onset has a small random push or pull
- **Velocity variation** — root notes are accented, upper extensions are softer, and base velocity varies between chords
- **Ring-out** — roughly 30% of chords have 1-2 notes that sustain into the next chord
- **Early release** — non-ringing notes lift slightly before the next chord, simulating a hand moving to the next shape

The MIDI instrument is set to nylon string guitar (program 25). A fixed random seed (42) makes output reproducible.

```sh
python3 generate_midi_with_variance.py input.txt output.mid
```

Defaults to `moolight.txt` / `moolight_with_variance.mid` if no arguments are given.

## Example

The `example/` folder contains a sample progression and its generated output:

- [`example/moolight.txt`](example/moolight.txt) — input chord progression (54 chords, 114 total beats)
- [`example/moolight.mid`](example/moolight.mid) — clean MIDI output
- [`example/moolight_with_variance.mid`](example/moolight_with_variance.mid) — humanized MIDI output

To regenerate the example outputs:

```sh
python3 generate_midi.py example/moolight.txt example/moolight.mid
python3 generate_midi_with_variance.py example/moolight.txt example/moolight_with_variance.mid
```

## Dependencies

- Python 3
- [MIDIUtil](https://pypi.org/project/MIDIUtil/) — `pip install midiutil`
