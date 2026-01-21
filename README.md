# Trello API Client

A Python client to read cards from your Trello boards using the Trello REST API.

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd trello_api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Trello API credentials:
   - Get your API key from: https://trello.com/app-key
   - Generate a token from: https://trello.com/1/authorize?expiration=never&scope=read&response_type=token&name=Trello%20API%20Client&key=YOUR_API_KEY
   - Replace `YOUR_API_KEY` with your actual API key in the URL above

4. Create a `.env` file with your credentials:
```
TRELLO-API-KEY=your_api_key_here
TRELLO-SECRET=your_secret_here
TRELLO-TOKEN=your_token_here
```

## Usage

Run the main script to fetch cards from the "True Crime Video Dubs" board:

```bash
python trello_client.py
```

This will:
- Display all cards grouped by their lists
- Show card details including labels, due dates, and descriptions
- Save raw data to `trello_cards.json` for further processing

## API Methods

The `TrelloClient` class provides the following methods:

- `get_boards()`: Get all boards for the authenticated user
- `find_board_by_name(name)`: Find a board by its name
- `get_board_cards(board_id)`: Get all cards in a specific board
- `get_lists_on_board(board_id)`: Get all lists in a board
- `get_board_cards_with_lists(board_name)`: Get cards grouped by lists for a board

## Project Structure

```
trello_api/
├── .env                # API credentials (gitignored)
├── .gitignore          # Git ignore file
├── requirements.txt    # Python dependencies
├── trello_client.py    # Main client script
├── trello_cards.json   # Output data (generated)
└── README.md          # This file
```

## Notes

- This client only reads data from Trello (no modifications)
- The API token should have read-only permissions
- Make sure to keep your `.env` file secure and never commit it to version control
