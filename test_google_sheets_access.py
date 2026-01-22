"""
Test script to check if we can access Google Sheets data from the links in Trello cards.
This is a test only - not for implementation yet.
"""

import json
import re
import requests

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def extract_google_sheets_links(data):
    """Extract all Google Sheets links from Trello data."""
    sheets_links = []
    
    for list_name, cards in data['cards_by_list'].items():
        for card in cards:
            # Check description
            desc = card.get('desc', '')
            if desc:
                # Find Google Sheets URLs
                pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)'
                matches = re.findall(pattern, desc)
                for match in matches:
                    sheets_links.append({
                        'card_name': card['name'],
                        'list': list_name,
                        'spreadsheet_id': match,
                        'url': f'https://docs.google.com/spreadsheets/d/{match}'
                    })
    
    return sheets_links

def test_google_sheets_access():
    """Test different methods to access Google Sheets data."""
    
    print("="*60)
    print("TESTING GOOGLE SHEETS ACCESS")
    print("="*60)
    
    # Load data
    data = load_trello_data()
    sheets_links = extract_google_sheets_links(data)
    
    print(f"\nFound {len(sheets_links)} Google Sheets links in Trello cards")
    
    if not sheets_links:
        print("No Google Sheets links found to test.")
        return
    
    # Test with first link
    test_link = sheets_links[0]
    print(f"\nTesting with: {test_link['card_name']}")
    print(f"Spreadsheet ID: {test_link['spreadsheet_id']}")
    print(f"URL: {test_link['url']}")
    
    print("\n" + "-"*60)
    print("METHOD 1: Direct CSV Export (Public sheets only)")
    print("-"*60)
    
    # Try to access as CSV export (works only for public sheets)
    csv_url = f"https://docs.google.com/spreadsheets/d/{test_link['spreadsheet_id']}/export?format=csv"
    print(f"Trying: {csv_url}")
    
    try:
        response = requests.get(csv_url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! Sheet is publicly accessible")
            print(f"Content preview (first 200 chars):\n{response.text[:200]}")
        elif response.status_code == 401 or response.status_code == 403:
            print("❌ FAILED: Sheet requires authentication")
        else:
            print(f"❌ FAILED: Unexpected status code")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "-"*60)
    print("METHOD 2: Google Sheets API (Requires API Key)")
    print("-"*60)
    print("To use Google Sheets API, you would need:")
    print("1. Enable Google Sheets API in Google Cloud Console")
    print("2. Create API credentials (API Key or OAuth)")
    print("3. Use the google-api-python-client library")
    print("4. Make authenticated requests")
    
    print("\nExample API endpoint:")
    print(f"https://sheets.googleapis.com/v4/spreadsheets/{test_link['spreadsheet_id']}")
    
    print("\n" + "-"*60)
    print("SUMMARY")
    print("-"*60)
    print("✓ If sheets are PUBLIC: Can download as CSV/Excel directly")
    print("✓ If sheets are PRIVATE: Need Google Sheets API with OAuth")
    print("✓ Trello API Key won't work for Google Sheets")
    print("\nRecommendation:")
    print("- Check if your Google Sheets are set to 'Anyone with link can view'")
    print("- If yes: Easy CSV export without authentication")
    print("- If no: Need to set up Google Sheets API credentials")

if __name__ == "__main__":
    test_google_sheets_access()
