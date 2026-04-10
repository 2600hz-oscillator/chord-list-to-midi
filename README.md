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

### `generate_triad_midi.py`

Reduces each chord to its 3 most dominant notes (root, third, and the most colorful remaining note) and writes them to a 3-track MIDI file — one monophonic voice per track. This lets you route each voice to a separate synth.

Note selection priority: root is always kept, then the third (or sus4), then the most characteristic remaining interval (7th > extensions > 6th > 5th).

```sh
python3 generate_triad_midi.py input.txt output.mid
```

Defaults to `moolight.txt` / `moolight_triad.mid` if no arguments are given.

### `generate_triad_midi_with_variance.py`

Same 3-note, 3-track output as `generate_triad_midi.py`, but with keyboard-style humanization:

- **Voice asynchrony** — each voice gets an independent small timing offset (not a strum)
- **Phrase dynamics** — velocity follows a slow sine wave across the progression
- **Legato overlap** — ~60% of notes sustain slightly past the chord boundary (sustain pedal feel)
- **Anticipation** — the inner voice occasionally attacks slightly before the beat
- **Even voicing** — no systematic root accent (unlike the guitar variant)

```sh
python3 generate_triad_midi_with_variance.py input.txt output.mid
```

Defaults to `moolight.txt` / `moolight_triad_with_variance.mid` if no arguments are given.

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
- [`example/moolight_with_variance.mid`](example/moolight_with_variance.mid) — humanized MIDI output (guitar style)
- [`example/moolight_triad.mid`](example/moolight_triad.mid) — 3-track triad MIDI output
- [`example/moolight_triad_with_variance.mid`](example/moolight_triad_with_variance.mid) — 3-track triad MIDI output (keyboard style)

To regenerate the example outputs:

```sh
python3 generate_midi.py example/moolight.txt example/moolight.mid
python3 generate_midi_with_variance.py example/moolight.txt example/moolight_with_variance.mid
python3 generate_triad_midi.py example/moolight.txt example/moolight_triad.mid
python3 generate_triad_midi_with_variance.py example/moolight.txt example/moolight_triad_with_variance.mid
```

## Dependencies

All dependencies are managed by [Flox](https://flox.dev). To set up the environment:

```sh
flox activate
```

This provides Python 3 and [MIDIUtil](https://pypi.org/project/MIDIUtil/) — no manual `pip install` needed.

## AI Use Disclosure

Made with Claude Code
