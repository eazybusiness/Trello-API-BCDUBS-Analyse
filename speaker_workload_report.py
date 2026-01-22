import json
from datetime import datetime
from collections import defaultdict

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_speaker_workload(data):
    """Analyze workload for speakers from the 'Skripte zur Aufnahme' list."""
    cards = data['cards_by_list'].get('Skripte zur Aufnahme', [])
    
    # Dictionary to store speaker data
    speaker_data = defaultdict(lambda: {
        'completed_tasks': 0,
        'uncompleted_tasks': 0,
        'cards': [],
        'upcoming_due_dates': []
    })
    
    # Process each card
    for card in cards:
        card_name = card['name']
        card_due = card.get('due')
        card_url = card.get('shortUrl', '')
        
        # Get members assigned to this card
        members = card.get('members', [])
        
        # Process checklists
        for checklist in card.get('checklists', []):
            checklist_name = checklist.get('name', 'Checkliste')
            items = checklist.get('checkItems', [])  # Changed from 'items' to 'checkItems'
            
            for item in items:
                item_name = item.get('name', '')
                item_state = item.get('state', 'incomplete')
                
                # Extract speaker name from checklist item
                # Common patterns: "Lucas", "Nils", "Chaos", etc.
                speaker_names = ['Lucas', 'Nils', 'Chaos', 'Marcel', 'Holger', 'Marco', 'Martin', 'Drystan', 'Belli', 'Sira', 'Jade', 'Jessica']
                found_speaker = None
                
                for name in speaker_names:
                    if name.lower() in item_name.lower():
                        found_speaker = name
                        break
                
                # If no speaker found in item name, check if item is assigned to card members
                if not found_speaker and members:
                    # For items without speaker names, count for all card members
                    for member in members:
                        member_name = member.get('fullName', '').split()[0]  # Use first name
                        if member_name in speaker_names:
                            found_speaker = member_name
                            if item_state == 'complete':
                                speaker_data[found_speaker]['completed_tasks'] += 1
                            else:
                                speaker_data[found_speaker]['uncompleted_tasks'] += 1
                            
                            # Add card info
                            card_info = {
                                'card_name': card_name,
                                'checklist': checklist_name,
                                'item': item_name,
                                'status': item_state,
                                'due_date': card_due,
                                'url': card_url
                            }
                            speaker_data[found_speaker]['cards'].append(card_info)
                            
                            # Track due dates
                            if card_due and item_state == 'incomplete':
                                speaker_data[found_speaker]['upcoming_due_dates'].append(card_due)
                else:
                    # If speaker found in item name
                    if found_speaker:
                        if item_state == 'complete':
                            speaker_data[found_speaker]['completed_tasks'] += 1
                        else:
                            speaker_data[found_speaker]['uncompleted_tasks'] += 1
                        
                        # Add card info
                        card_info = {
                            'card_name': card_name,
                            'checklist': checklist_name,
                            'item': item_name,
                            'status': item_state,
                            'due_date': card_due,
                            'url': card_url
                        }
                        speaker_data[found_speaker]['cards'].append(card_info)
                        
                        # Track due dates
                        if card_due and item_state == 'incomplete':
                            speaker_data[found_speaker]['upcoming_due_dates'].append(card_due)
    
    return speaker_data

def generate_report(speaker_data):
    """Generate a formatted report of speaker workload."""
    print("=" * 80)
    print("SPEAKER WORKLOAD REPORT - Skripte zur Aufnahme")
    print("=" * 80)
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Sort speakers by total tasks (completed + uncompleted)
    sorted_speakers = sorted(speaker_data.items(), 
                           key=lambda x: x[1]['completed_tasks'] + x[1]['uncompleted_tasks'], 
                           reverse=True)
    
    for speaker, data in sorted_speakers:
        total_tasks = data['completed_tasks'] + data['uncompleted_tasks']
        completion_rate = (data['completed_tasks'] / total_tasks * 100) if total_tasks > 0 else 0
        
        print(f"🎤 {speaker}")
        print(f"   Total Tasks: {total_tasks}")
        print(f"   ✅ Completed: {data['completed_tasks']}")
        print(f"   ⏳ Pending: {data['uncompleted_tasks']}")
        print(f"   📊 Completion Rate: {completion_rate:.1f}%")
        
        # Show upcoming due dates
        if data['upcoming_due_dates']:
            # Sort due dates
            sorted_dates = sorted(data['upcoming_due_dates'])
            print(f"   📅 Upcoming Due Dates:")
            for date_str in sorted_dates[:3]:  # Show next 3 due dates
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    days_until = (date_obj - datetime.now()).days
                    status = "OVERDUE!" if days_until < 0 else f"in {days_until} days"
                    print(f"      - {date_str[:10]} ({status})")
                except:
                    print(f"      - {date_str[:10]}")
        
        # Show card details
        if data['cards']:
            print(f"   📋 Assigned Cards:")
            # Group cards by status
            pending_cards = [c for c in data['cards'] if c['status'] == 'incomplete']
            completed_cards = [c for c in data['cards'] if c['status'] == 'complete']
            
            if pending_cards:
                print(f"      Pending ({len(pending_cards)}):")
                for card in pending_cards[:5]:  # Show first 5
                    due_info = f" (Due: {card['due_date'][:10]})" if card['due_date'] else ""
                    print(f"        • {card['card_name']}{due_info}")
                if len(pending_cards) > 5:
                    print(f"        ... and {len(pending_cards) - 5} more pending tasks")
            
            if completed_cards:
                print(f"      Completed ({len(completed_cards)}):")
                for card in completed_cards[:3]:  # Show first 3
                    print(f"        • {card['card_name']}")
                if len(completed_cards) > 3:
                    print(f"        ... and {len(completed_cards) - 3} more completed tasks")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("Most Busy Speakers:")
    busiest = sorted(speaker_data.items(), 
                    key=lambda x: x[1]['completed_tasks'] + x[1]['uncompleted_tasks'], 
                    reverse=True)[:3]
    for i, (speaker, data) in enumerate(busiest, 1):
        total = data['completed_tasks'] + data['uncompleted_tasks']
        print(f"  {i}. {speaker}: {total} tasks")
    
    print("\nHighest Completion Rates:")
    best_rates = sorted([(s, d) for s, d in speaker_data.items() 
                        if (d['completed_tasks'] + d['uncompleted_tasks']) > 0],
                       key=lambda x: x[1]['completed_tasks'] / (x[1]['completed_tasks'] + x[1]['uncompleted_tasks']),
                       reverse=True)[:3]
    for i, (speaker, data) in enumerate(best_rates, 1):
        total = data['completed_tasks'] + data['uncompleted_tasks']
        rate = data['completed_tasks'] / total * 100
        print(f"  {i}. {speaker}: {rate:.1f}% ({data['completed_tasks']}/{total})")
    
    print("\nSpeakers with Overdue Tasks:")
    overdue = []
    for speaker, data in speaker_data.items():
        for date_str in data['upcoming_due_dates']:
            try:
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if (date_obj - datetime.now()).days < 0:
                    overdue.append(speaker)
                    break
            except:
                pass
    if overdue:
        for speaker in set(overdue):
            print(f"  ⚠️  {speaker}")
    else:
        print("  ✅ No overdue tasks found!")

def save_detailed_report(speaker_data, filename='reports/speaker_workload_detailed.json'):
    """Save detailed speaker data to JSON file."""
    # Convert defaultdict to regular dict for JSON serialization
    export_data = dict(speaker_data)
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    print(f"\nDetailed report saved to '{filename}'")

def main():
    # Load Trello data
    data = load_trello_data()
    
    # Analyze workload
    speaker_data = analyze_speaker_workload(data)
    
    # Generate report
    generate_report(speaker_data)
    
    # Save detailed data
    save_detailed_report(speaker_data)

if __name__ == "__main__":
    main()
