# Gagen Calculator (Wage Calculator)

## Overview

This script automatically calculates wages for voice actors based on script data stored in Google Sheets. It analyzes the script length, line counts per speaker, and generates a detailed Excel report with wage calculations.

## Features

- ✅ Checks if `gagen.xlsx` already exists as a Trello attachment
- ✅ Downloads and analyzes Google Sheets script data
- ✅ Parses timecodes to calculate total script duration
- ✅ Counts lines per speaker
- ✅ Calculates wages based on configurable rates
- ✅ Supports Express projects (higher rate)
- ✅ Generates professional Excel reports
- ✅ **Read-only mode** - protects production Trello data

## Requirements

```bash
pip install pandas==2.1.4 openpyxl==3.1.2
```

Or install all project dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
source venv/bin/activate
python calculate_gagen.py
```

The script will:
1. Search for cards in the "Skripte zur Aufnahme" list
2. Check if `gagen.xlsx` already exists as attachment
3. If not, download the Google Sheets from the card description
4. Analyze the script data
5. Calculate wages
6. Generate an Excel file locally

### Google Sheets Requirements

The Google Sheet must be:
- **Publicly accessible** (set to "Anyone with link can view")
- Structured with the following columns:
  - Column A: Voices (speaker category)
  - Column B: Paragraph index (line number)
  - Column C: Speaker (speaker name)
  - Column D: Start time (timecode)
  - Column E: End time (timecode)
  - Column F: German text
  - Column G: English text

### Timecode Format

Timecodes should be in format: `HH:MM:SS:FF`
- Example: `00:05:23:12` = 5 minutes, 23 seconds, 12 frames

The script will parse the last timecode in column E to determine total duration.

## Wage Calculation Formula

### Standard Rate
```
Base Rate = 8.75 * Total Minutes / Total Lines
Wage per Speaker = Base Rate * Lines per Speaker
```

### Express Rate
If the Trello card has an "Express" label:
```
Base Rate = 9.75 * Total Minutes / Total Lines
Wage per Speaker = Base Rate * Lines per Speaker
```

## Output

The script generates an Excel file named `gagen_[CARD_ID].xlsx` with three sheets:

### 1. Zusammenfassung (Summary)
- Calculation parameters
- Total minutes
- Total lines
- Base rate per line

### 2. Sprecher (Speakers)
- Speaker name
- Gender (männlich/weiblich/unbekannt) - extracted from Voices column
- Number of lines
- Calculated wage in USD

### 3. Charaktergruppen (Character Groups)
- Character group name
- Number of lines
- Calculated wage in USD

**Note:** Character group analysis by background color is not available when using CSV export. To enable this feature, Google Sheets API with authentication would be required.

## Important Notes

### Read-Only Mode
The script operates in **read-only mode** to protect production Trello data. Excel files are created **locally only** and are **not automatically uploaded** to Trello.

To upload the file to Trello, you would need:
- Write permissions on the Trello API
- Manual upload or additional script modification

### Character Group Colors

The script is designed to recognize these character groups by background color:
- **Zivis**: Blue (`#4f81bd`)
- **Cops**: Red (`#c0504d`)
- **Weibliche Sprecher**: Orange (`#f79646`)
- **Erzähler**: Green (`#9bbb59`)

However, CSV export does not include formatting data. To extract colors, you would need to:
1. Set up Google Sheets API credentials
2. Use the Sheets API to read cell formatting
3. Modify the script to use API instead of CSV export

## Troubleshooting

### "Google Sheet is not publicly accessible"
- Open the Google Sheet
- Click "Share" → "Anyone with link can view"
- Try again

### "No Google Sheets URL found in card description"
- Ensure the card description contains a valid Google Sheets link
- Format: `https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]`

### "Total Minutes is 0"
- Check that column E contains valid timecodes
- Ensure timecodes are in format `HH:MM:SS:FF` or `HH:MM:SS`
- Verify the last row has a timecode

## File Structure

```
calculate_gagen.py
├── ColorMatcher class
│   └── Color matching utilities (for future API integration)
└── GagenCalculator class
    ├── find_card_in_list()
    ├── check_attachment_exists()
    ├── extract_google_sheets_url()
    ├── download_google_sheet()
    ├── parse_timecode()
    ├── analyze_script_data()
    ├── check_express_label()
    ├── calculate_wages()
    ├── create_excel_report()
    └── run()
```

## Example Output

```
======================================================================
GAGEN-BERECHNUNG (Wage Calculation)
======================================================================

1. Searching for cards in list 'Skripte zur Aufnahme'...
✅ Found 2 card(s)

======================================================================
Processing card 1/2: when-cops-save-lives-last-moment
======================================================================

2. Checking for existing gagen.xlsx attachment...
ℹ️  gagen.xlsx not found. Proceeding with calculation.

3. Extracting Google Sheets URL from description...
✅ Found Google Sheets URL: https://docs.google.com/spreadsheets/d/...

4. Downloading and analyzing Google Sheet...
✅ Downloaded sheet with 557 rows and 8 columns

ℹ️  Using sum of speaker lines: 554

📊 Analysis Results:
   Total Minutes: 18
   Total Lines: 554
   Speakers found: 10

5. Checking for Express label...
ℹ️  No Express label. Using standard rate: $8.75

6. Calculating wages...

💰 Wage Calculation:
   Maximum budget: $157.5
   Base rate: $0.2843/line
   Total speakers: 10

7. Creating Excel report...

✅ Excel report created: gagen_69bc3ad5a851ed58114f5b1d.xlsx
✅ Processing complete for card: when-cops-save-lives-last-moment
   Output file: gagen_69bc3ad5a851ed58114f5b1d.xlsx

⚠️  NOTE: File created locally only (read-only mode to protect production data)
```

## Future Enhancements

- [ ] Google Sheets API integration for color extraction
- [ ] Automatic upload to Trello (requires write permissions)
- [ ] Support for multiple sheets per card
- [ ] Custom rate configuration via environment variables
- [ ] PDF report generation
- [ ] Email notification when wages are calculated

## License

Part of the Trello API project for True Crime Video Dubs workflow automation.

⚠️  NOTE: File created locally only (read-only mode to protect production data)
```

## Future Enhancements

- [ ] Google Sheets API integration for color extraction
- [ ] Automatic upload to Trello (requires write permissions)
- [ ] Support for multiple sheets per card
- [ ] Custom rate configuration via environment variables
- [ ] PDF report generation
- [ ] Email notification when wages are calculated

## License

Part of the Trello API project for True Crime Video Dubs workflow automation.
