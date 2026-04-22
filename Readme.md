# Slack TV

Scheduled bots that post content into Slack channels. One app, multiple personas — each channel gets its own bot identity and posting schedule.

## Structure

Each channel lives in its own subdirectory:

```
waste-land/    # Posts one line of The Waste Land per hour
```

A channel directory contains a `notifier.py` (what to post and how the bot appears), an `icon.png` (bot avatar), and a `poem.txt` or equivalent source file.

## Setup

See [SETUP.md](SETUP.md) for Slack app creation, GitHub secrets, and how to add new channels.

## Slack TV Channel Directory

- `waste-land/` - **The Waste Land, One Line Per Hour** — Eliot's poem is 434 lines. At one line per hour, it takes ~18 days to complete, then loops. The line-per-hour pace is critical: each line sits alone in the channel long enough to be read as a standalone fragment, which is how the poem actually works — collage, juxtaposition, voices interrupting each other. The footnotes post as threaded replies.
- `dactylic-odyssey/` - **The Odyssey in Dactylic Drip** — Post 5 lines of the Fagles (or Lattimore, or Fitzgerald) translation every 4 hours. The Odyssey is ~12,110 lines. At 30 lines/day, the full poem takes ~403 days — just over a year. A 5-line chunk is roughly one complete Homeric image or action beat. The year-long duration mirrors the scale of the journey itself. When it finishes, start the Iliad.
- `golly-notifier/` - **Golly Postseason Notifications** — Tracks the [Golly](https://golly.life) postseason and posts game results, series updates, and schedule notifications. Two bot personas: **Star Cup** (Tuesday–Wednesday) and **Hellmouth Cup** (Friday–Sunday). Each checks the Golly API hourly during its window, reporting series starts, daily scores with replay links, series clinches, and cup winners. Scheduling: Star runs 5 AM–1 AM PT Tue, 5 AM–5 PM PT Wed; Hellmouth runs 8 AM–4 PM PT Fri, 8 AM–8 PM PT Sat–Sun.

