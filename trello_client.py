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

    def get_board_custom_fields(self, board_id: str) -> List[Dict[str, Any]]:
        """Get custom field definitions for a board."""
        url = f"{self.base_url}/boards/{board_id}/customFields"
        params = {
            'key': self.api_key,
            'token': self.token
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
    
    def get_card_details(self, card_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific card including comments, members, and checklists."""
        # Get basic card info
        url = f"{self.base_url}/cards/{card_id}"
        params = {
            'key': self.api_key,
            'token': self.token,
            'fields': 'name,id,idBoard,desc,due,dateLastActivity,labels,idList,closed,shortUrl',
            'attachments': 'cover',
            'members': 'true',
            'member_fields': 'fullName,username,avatarUrl',
            'checklists': 'all',
            'checklist_fields': 'name,id,idCard,pos,nameItems',
            'actions': 'commentCard',
            'actions_limit': 1000,
            'action_fields': 'date,type,data,memberCreator',
            'action_memberCreator_fields': 'fullName,username',
            'customFieldItems': 'true'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        card_data = response.json()
        
        # Get checklist items for each checklist
        for checklist in card_data.get('checklists', []):
            try:
                checklist_url = f"{self.base_url}/checklists/{checklist['id']}/items"
                checklist_params = {
                    'key': self.api_key,
                    'token': self.token,
                    'fields': 'name,state,pos,idCheckItem'
                }
                checklist_response = requests.get(checklist_url, params=checklist_params)
                checklist_response.raise_for_status()
                checklist['items'] = checklist_response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Checklist might be deleted or inaccessible
                    checklist['items'] = []
                    print(f"    Warning: Could not fetch items for checklist '{checklist['name']}'")
                else:
                    raise
        
        return card_data
    
    def get_board_cards_with_lists(self, board_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all cards grouped by their lists for a specific board with full details."""
        board = self.find_board_by_name(board_name)
        board_id = board['id']
        
        lists = self.get_lists_on_board(board_id)
        custom_fields = self.get_board_custom_fields(board_id)
        cards = self.get_board_cards(board_id)
        
        # Create a dictionary with list names as keys
        cards_by_list = {lst['name']: [] for lst in lists}
        list_id_to_name = {lst['id']: lst['name'] for lst in lists}
        
        # Group cards by list and fetch detailed information
        print(f"Fetching detailed information for {len(cards)} cards...")
        for i, card in enumerate(cards, 1):
            print(f"  Processing card {i}/{len(cards)}: {card['name']}")
            list_name = list_id_to_name.get(card['idList'], 'Unknown')
            detailed_card = self.get_card_details(card['id'])
            cards_by_list[list_name].append(detailed_card)
        
        return {
            'board': board,
            'custom_fields': custom_fields,
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
                print(f"\n  {status} {card['name']}{label_str}{due_str}")
                print(f"    URL: {card.get('shortUrl', 'N/A')}")
                
                # Show members
                if card.get('members'):
                    members = ", ".join([f"{m['fullName']}(@{m['username']})" for m in card['members']])
                    print(f"    Members: {members}")
                
                # Show description
                if card.get('desc'):
                    desc = card['desc']
                    if len(desc) > 150:
                        desc = desc[:150] + "..."
                    print(f"    Description: {desc}")
                
                # Show comments
                comments = [action for action in card.get('actions', []) if action['type'] == 'commentCard']
                if comments:
                    print(f"    Comments ({len(comments)}):")
                    for comment in comments[-3:]:  # Show last 3 comments
                        creator = comment.get('memberCreator', {}).get('fullName', 'Unknown')
                        date = comment['date'][:10]  # Just show date part
                        text = comment['data']['text']
                        if len(text) > 100:
                            text = text[:100] + "..."
                        print(f"      - {date} by {creator}: {text}")
                
                # Show checklists
                if card.get('checklists'):
                    print(f"    Checklists:")
                    for checklist in card['checklists']:
                        completed = sum(1 for item in checklist.get('items', []) if item['state'] == 'complete')
                        total = len(checklist.get('items', []))
                        print(f"      - {checklist['name']}: {completed}/{total} completed")
                        if total > 0:
                            for item in checklist['items'][:5]:  # Show first 5 items
                                status = "✓" if item['state'] == 'complete' else "○"
                                print(f"        {status} {item['name']}")
                            if total > 5:
                                print(f"        ... and {total - 5} more items")
        
        # Also save raw data to a file for later processing
        import json
        with open('trello_cards_detailed.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nRaw detailed data saved to 'trello_cards_detailed.json'")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
