import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any

class TrelloClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('TRELLO-API-KEY')
        self.token = os.getenv('TRELLO-TOKEN')
        self.base_url = "https://api.trello.com/1"
        
        if not self.api_key or not self.token:
            raise ValueError("TRELLO-API-KEY and TRELLO-TOKEN must be set in .env file")
    
    def get_boards(self) -> List[Dict[str, Any]]:
        """Get all boards for the authenticated user."""
        url = f"{self.base_url}/members/me/boards"
        params = {
            'key': self.api_key,
            'token': self.token,
            'fields': 'name,id,desc'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def find_board_by_name(self, board_name: str) -> Dict[str, Any]:
        """Find a board by its name."""
        boards = self.get_boards()
        for board in boards:
            if board['name'] == board_name:
                return board
        raise ValueError(f"Board '{board_name}' not found")
    
    def get_board_cards(self, board_id: str) -> List[Dict[str, Any]]:
        """Get all cards in a board."""
        url = f"{self.base_url}/boards/{board_id}/cards"
        params = {
            'key': self.api_key,
            'token': self.token,
            'fields': 'name,id,desc,due,dateLastActivity,labels,idList,closed',
            'attachments': 'cover'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_lists_on_board(self, board_id: str) -> List[Dict[str, Any]]:
        """Get all lists in a board."""
        url = f"{self.base_url}/boards/{board_id}/lists"
        params = {
            'key': self.api_key,
            'token': self.token,
            'fields': 'name,id'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_board_cards_with_lists(self, board_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all cards grouped by their lists for a specific board."""
        board = self.find_board_by_name(board_name)
        board_id = board['id']
        
        lists = self.get_lists_on_board(board_id)
        cards = self.get_board_cards(board_id)
        
        # Create a dictionary with list names as keys
        cards_by_list = {lst['name']: [] for lst in lists}
        list_id_to_name = {lst['id']: lst['name'] for lst in lists}
        
        # Group cards by list
        for card in cards:
            list_name = list_id_to_name.get(card['idList'], 'Unknown')
            cards_by_list[list_name].append(card)
        
        return {
            'board': board,
            'cards_by_list': cards_by_list
        }

def main():
    client = TrelloClient()
    
    try:
        # Get cards from "True Crime Video Dubs" board
        board_name = "True Crime Video Dubs"
        print(f"Fetching cards from board: {board_name}")
        
        result = client.get_board_cards_with_lists(board_name)
        
        print(f"\nBoard: {result['board']['name']}")
        print(f"Description: {result['board'].get('desc', 'No description')}")
        print(f"Board ID: {result['board']['id']}")
        
        print("\nCards by list:")
        for list_name, cards in result['cards_by_list'].items():
            print(f"\n--- {list_name} ({len(cards)} cards) ---")
            for card in cards:
                status = "✓" if card['closed'] else "○"
                labels = ", ".join([label['name'] for label in card.get('labels', [])])
                label_str = f" [{labels}]" if labels else ""
                due_str = f" (Due: {card['due']})" if card['due'] else ""
                print(f"  {status} {card['name']}{label_str}{due_str}")
                if card.get('desc'):
                    print(f"    Description: {card['desc'][:100]}{'...' if len(card['desc']) > 100 else ''}")
        
        # Also save raw data to a file for later processing
        import json
        with open('trello_cards.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nRaw data saved to 'trello_cards.json'")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
