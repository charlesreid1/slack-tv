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
