[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/iuYZxbvR)

# Unistroke Gesture Recognition — Assignment 06

## Setup

- Python **3.10.12**
- Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

The project is split into three folders, one per part.

---

## Part 1 — Gesture Input & Recognizer

Contains the `$1` gesture recognizer (`recognizer.py`) used here and by Parts 2 and 3.

Run the gesture input app directly, it shows a live visualization of every step of the recognition pipeline (resampling, rotation, scaling, and template matching:

```bash
python Part_1/gesture_input.py
```

## Part 2 — LSTM vs. $1 Comparison

Fully documented in `Part_2/unistroke_gestures.ipynb`. er notebook Part_2/unistroke_gestures.ipynb

The notebook trains and compares three LSTM variants against the $1 recognizer (with varying template counts), evaluated on both the original Wobbrock dataset and a self-recorded gesture set.

## Part 3 — Spell Duel (game)

A turn-based duel between you and an AI wizard, rendered in ASCII stick-figure art. Cast spells by drawing unistroke gestures, the trained LSTM (V2) recognizes your gesture, and its confidence score determines how powerful your spell turns out. Low-confidence casts can fizzle entirely.

Spells follow a rock-paper-scissors-style elemental cycle, plus shielding and healing mechanics, better left to discover by playing.

Run it with:

```bash
python Part_3/spell_duel.py
```

> Requires the trained model exported from the Part 2 notebook (`spell_model_v2.keras` and `spell_label_encoder.pkl`) to be present in `Part_3/`.