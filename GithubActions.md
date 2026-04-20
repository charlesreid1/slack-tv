# Gitea Actions Workflow Guide

Workflows run on a self-hosted Gitea Actions runner (not GitHub Actions). Follow these principles to keep runs fast and lean.

## Runner and available images

The runner is configured in the `pod-charlesreid1` repository under `d-gitea/runner/config.yaml`. Available labels and their backing Docker images:

| Label | Image |
|---|---|
| `alpine` | `python:3.12-alpine` (~50 MB, has python3+pip; install extras with `apk add --no-cache`) |
| `ubuntu-latest` | `catthehacker/ubuntu:act-22.04` |
| `ubuntu-22.04` | `catthehacker/ubuntu:act-22.04` |
| `ubuntu-20.04` | `catthehacker/ubuntu:act-20.04` |
| `ubuntu-24.04` | `catthehacker/ubuntu:act-22.04` |

If a channel needs a container image that isn't listed above, add a new label entry in `pod-charlesreid1/d-gitea/runner/config.yaml`.

Use `ubuntu-latest` for most channels.

## Steps

A channel workflow has four steps:

1. Checkout the repository (`actions/checkout@v4`)
2. Set up Python (`actions/setup-python@v5`, version `3.11`)
3. Install dependencies (`pip install -r channel-name/requirements.txt`)
4. Run the script

## Template

```yaml
name: Channel Name

on:
  schedule:
    - cron: '5 * * * *'
  workflow_dispatch:

jobs:
  post-line:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r channel-name/requirements.txt

      - name: Post next line to Slack
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_ID: ${{ secrets.CHANNEL_NAME_CHANNEL_ID }}
        run: python channel-name/notifier.py
```
