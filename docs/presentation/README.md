# Rovust presentation

## Present it (day of the discussion)

**Online — Claude Slides (transitions, animated map, speaker notes):**

- English speaker notes: https://claude.ai/artifact/VnwvfuttPtvHGe81Xfyhb9
- Egyptian-Arabic speaker notes: https://claude.ai/artifact/F9q2YYt6BtYD7pJ3d9Ddok

Open the link signed in to claude.ai, press **Present**, then F11 for full screen.
Arrow keys move between slides. Read the notes from a phone (same link, or
`SPEAKER_NOTES.md`). The decks are private until shared from the page's Share menu.

**Offline backup:**

1. `Rovust_presentation.html` — double-click, press **F** for full screen
   (N = notes, L = English / Egyptian notes). The map GIF moves; no transitions.
2. `Rovust_presentation.pptx` / `Rovust_presentation_ar_notes.pptx` — PowerPoint
   with the slides as pictures and the notes in presenter view.
3. `Rovust_presentation.pdf` — works anywhere.

## Files

| File | What it is |
|---|---|
| `slides/*.html`, `deck.json`, `notes_ar.json` | the slide sources (same as Claude Slides) |
| `Rovust_presentation.html` | standalone web viewer, both note languages |
| `Rovust_presentation.pdf` | 30 pages |
| `Rovust_presentation.pptx` | PowerPoint, English notes |
| `Rovust_presentation_ar_notes.pptx` | PowerPoint, Egyptian-Arabic notes |
| `SPEAKER_NOTES.md` | all notes, both languages |

Rebuild everything after editing a slide: `python tools/build_presentation.py`
(renders with headless Edge/Chrome; needs python-pptx and Pillow in the venv).
