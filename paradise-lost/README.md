# Paradise Lost — Hourly Drip

Posts one line of John Milton's *Paradise Lost* (1667) to a Slack channel every hour.

The poem has 12 books. The bot username and icon change per book — "Paradise Lost Book I" with `icon01.png`, "Paradise Lost Book II" with `icon02.png`, etc.

## How the line index works

Line selection is deterministic: `(unix_epoch_seconds // 3600) % total_lines`. This means:

- No state file needed — the script is stateless
- Any run at the same clock-hour produces the same line
- Manual reruns and retries are idempotent
- The sequence advances automatically across months and years

## How book detection works

The script scans backward from the current line to find the most recent "Book I", "Book II", etc. marker. This determines:

- **Bot username**: "Paradise Lost Book III"
- **Bot icon**: `icon03.png`

## Files

```
paradise-lost/
├── notifier.py       # The script
├── poem.txt          # The full text (12 books, markers like "Book I")
├── icon01.png        # Bot avatar for Book I
├── icon02.png        # Bot avatar for Book II
├── ...               # (one icon per book)
├── icon12.png        # Bot avatar for Book XII
├── requirements.txt  # Python dependencies
└── README.md
```

## Running locally

```bash
cd paradise-lost
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
SLACK_BOT_TOKEN=xoxb-... SLACK_CHANNEL_ID=C012AB3CD python notifier.py
```
