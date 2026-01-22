import json
import csv
from datetime import datetime

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def export_workload_to_csv(data, output_file='reports/speaker_workload.csv'):
    """Export speaker workload data to CSV format."""
    
    # Get cards from "Skripte zur Aufnahme"
    cards = data['cards_by_list'].get('Skripte zur Aufnahme', [])
    
    # Speaker names to track
    speaker_names = ['Lucas', 'Nils', 'Chaos', 'Marcel', 'Holger', 'Marco', 'Martin', 'Drystan', 'Belli', 'Sira', 'Jade', 'Jessica']
    
    # Prepare CSV data
    rows = []
    
    # Header
    rows.append([
        'Card Name',
        'Card URL',
        'Due Date',
        'Speaker',
        'Task Status',
        'Checklist Name',
        'Item Name',
        'Days Until Due'
    ])
    
    # Process each card
    for card in cards:
        card_name = card['name']
        card_url = card.get('shortUrl', '')
        card_due = card.get('due')
        
        # Calculate days until due
        days_until_due = ''
        if card_due:
            try:
                due_date = datetime.fromisoformat(card_due.replace('Z', '+00:00'))
                days_until = (due_date - datetime.now()).days
                days_until_due = str(days_until)
            except:
                days_until_due = ''
        
        # Process checklists
        for checklist in card.get('checklists', []):
            checklist_name = checklist.get('name', 'Checkliste')
            items = checklist.get('checkItems', [])
            
            for item in items:
                item_name = item.get('name', '')
                item_state = item.get('state', 'incomplete')
                
                # Find speaker in item name
                found_speaker = None
                for name in speaker_names:
                    if name.lower() in item_name.lower():
                        found_speaker = name
                        break
                
                # If speaker found, add row
                if found_speaker:
                    rows.append([
                        card_name,
                        card_url,
                        card_due[:10] if card_due else '',
                        found_speaker,
                        item_state,
                        checklist_name,
                        item_name,
                        days_until_due
                    ])
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)
    
    print(f"Workload data exported to '{output_file}'")
    
    # Print summary
    print(f"\nExport Summary:")
    print(f"- Total rows: {len(rows) - 1}")  # Subtract header
    print(f"- Cards processed: {len(cards)}")
    
    # Count tasks per speaker
    speaker_counts = {}
    for row in rows[1:]:  # Skip header
        speaker = row[3]
        status = row[4]
        if speaker not in speaker_counts:
            speaker_counts[speaker] = {'completed': 0, 'pending': 0}
        if status == 'complete':
            speaker_counts[speaker]['completed'] += 1
        else:
            speaker_counts[speaker]['pending'] += 1
    
    print("\nTask Summary:")
    for speaker, counts in sorted(speaker_counts.items(), key=lambda x: x[1]['completed'] + x[1]['pending'], reverse=True):
        total = counts['completed'] + counts['pending']
        print(f"- {speaker}: {total} tasks ({counts['completed']} completed, {counts['pending']} pending)")

def main():
    # Load data
    data = load_trello_data()
    
    # Export to CSV
    export_workload_to_csv(data)

if __name__ == "__main__":
    main()
