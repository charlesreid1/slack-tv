# GitHub Actions Workflow Guide

When creating workflows for new Slack TV channels, follow these principles to keep runs fast and cheap.

## Use what the runner already has

`ubuntu-latest` comes with Python 3, `requests`, and `pytz` preinstalled. Do not add a `setup-python` step or create a virtual environment unless you need a package that isn't already on the runner.

```yaml
# Good: just run the script directly
- run: python channel-name/notifier.py

# Bad: unnecessary setup
- uses: actions/setup-python@v6
- run: |
    python -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python notifier.py
```

If a future channel needs packages beyond what the runner provides, install them with `pip install --quiet` directly (no venv).

## Sparse checkout

Each workflow only needs its own channel directory. Use sparse checkout so the runner doesn't clone the entire repo.

```yaml
- uses: actions/checkout@v5
  with:
    sparse-checkout: channel-name
    sparse-checkout-cone-mode: true
```

## Minimal step count

A channel workflow should have exactly two steps:

1. Sparse checkout of the channel directory
2. Run the script

## Template

```yaml
name: Channel Name

on:
  schedule:
    - cron: '0 * * * *'
  workflow_dispatch:

jobs:
  post-line:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout channel directory
        uses: actions/checkout@v5
        with:
          sparse-checkout: channel-name
          sparse-checkout-cone-mode: true

      - name: Post next line to Slack
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_ID: ${{ secrets.CHANNEL_NAME_CHANNEL_ID }}
        run: python channel-name/notifier.py
```
