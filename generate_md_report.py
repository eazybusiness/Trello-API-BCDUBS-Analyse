import json
from datetime import datetime
from collections import defaultdict
from speaker_profiles import get_speaker_profile

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_speaker_data(data):
    """Analyze speaker workload and return structured data."""
    cards = data['cards_by_list'].get('Skripte zur Aufnahme', [])
    review_cards = data['cards_by_list'].get('In Review', [])
    done_cards = data['cards_by_list'].get('Fertig', [])
    
    # Dictionary to store speaker data
    speaker_data = defaultdict(lambda: {
        'completed_tasks': 0,
        'uncompleted_tasks': 0,
        'cards': [],
        'upcoming_due_dates': []
    })
    
    speaker_names = list(get_speaker_profile.__globals__['SPEAKER_PROFILES'].keys())

    mentioned_speakers = set()
    for card in (review_cards + done_cards):
        haystack = f"{card.get('name', '')} {card.get('desc', '')}".lower()
        for name in speaker_names:
            if name.lower() in haystack:
                mentioned_speakers.add(name)
    
    # Process each card
    for card in cards:
        card_name = card['name']
        card_due = card.get('due')
        card_url = card.get('shortUrl', '')
        
        # Process checklists
        for checklist in card.get('checklists', []):
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
                
                if found_speaker:
                    if item_state == 'complete':
                        speaker_data[found_speaker]['completed_tasks'] += 1
                    else:
                        speaker_data[found_speaker]['uncompleted_tasks'] += 1
                        if card_due:
                            speaker_data[found_speaker]['upcoming_due_dates'].append(card_due)
                    
                    # Store card info
                    card_info = {
                        'card_name': card_name,
                        'status': item_state,
                        'due_date': card_due,
                        'url': card_url
                    }
                    speaker_data[found_speaker]['cards'].append(card_info)

    for name in mentioned_speakers:
        speaker_data[name]
    
    return speaker_data

def generate_markdown_report(speaker_data, output_file='reports/speaker_workload_report.md'):
    """Generate a Markdown report with analysis and warnings."""
    
    # Calculate totals and percentages
    total_tasks = sum(data['completed_tasks'] + data['uncompleted_tasks'] for data in speaker_data.values())
    
    # Sort speakers by total tasks
    sorted_speakers = sorted(speaker_data.items(), 
                           key=lambda x: x[1]['completed_tasks'] + x[1]['uncompleted_tasks'], 
                           reverse=True)
    
    # Generate report content
    report = []
    report.append("# 🎤 Speaker Workload Analysis Report")
    report.append("")
    report.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Board:** True Crime Video Dubs - Skripte zur Aufnahme")
    report.append("")
    
    # Warnings Section
    report.append("## ⚠️ WARNINGS")
    report.append("")
    
    # Find speakers with high workload or low completion
    warnings = []
    for speaker, data in speaker_data.items():
        total = data['completed_tasks'] + data['uncompleted_tasks']
        if total == 0:
            continue
            
        completion_rate = data['completed_tasks'] / total * 100
        
        # Warning criteria
        if data['uncompleted_tasks'] >= 5:
            warnings.append(f"🚨 **{speaker}** has {data['uncompleted_tasks']} uncompleted tasks and {data['completed_tasks']} completed.")
        elif completion_rate < 30 and total >= 3:
            warnings.append(f"⚠️ **{speaker}** has a low completion rate of {completion_rate:.1f}% ({data['completed_tasks']}/{total} tasks).")
        
        # Check for upcoming due dates
        if data['upcoming_due_dates']:
            next_due = min(data['upcoming_due_dates'])
            try:
                due_date = datetime.fromisoformat(next_due.replace('Z', '+00:00'))
                days_until = (due_date - datetime.now()).days
                if days_until <= 3 and days_until >= 0:
                    warnings.append(f"⏰ **{speaker}** has a task due in {days_until} days ({next_due[:10]}).")
            except:
                pass
    
    if warnings:
        for warning in warnings:
            report.append(f"- {warning}")
    else:
        report.append("✅ No critical warnings at this time.")
    report.append("")
    
    # Speaker Usage Table
    report.append("## 📊 Speaker Usage Overview")
    report.append("")
    report.append("| Speaker | Total Tasks | Completed | Pending | Completion Rate | Completion Rating | % of Total Workload |")
    report.append("|---------|-------------|-----------|---------|-----------------|-------------------|---------------------|")
    
    for speaker, data in sorted_speakers:
        total = data['completed_tasks'] + data['uncompleted_tasks']
        completion_rate = (data['completed_tasks'] / total * 100) if total > 0 else 0
        workload_percentage = (total / total_tasks * 100) if total_tasks > 0 else 0

        profile = get_speaker_profile(speaker)
        is_unavailable = profile['availability'] != 'Available'
        speaker_label = f"{speaker} 😴" if is_unavailable else speaker

        if total == 0:
            rating = "—"
        elif completion_rate == 100:
            rating = "✅ Excellent"
        elif completion_rate >= 70:
            rating = "👍 Good"
        elif completion_rate >= 40:
            rating = "⚠️ Fair"
        else:
            rating = "🚨 Low"

        report.append(
            f"| {speaker_label} | {total} | {data['completed_tasks']} | {data['uncompleted_tasks']} | {completion_rate:.1f}% | {rating} | {workload_percentage:.1f}% |"
        )
    
    report.append("")
    
    # Detailed Speaker Analysis
    report.append("## 📋 Detailed Speaker Analysis")
    report.append("")
    
    for speaker, data in sorted_speakers:
        total = data['completed_tasks'] + data['uncompleted_tasks']
        if total == 0:
            continue
        
        completion_rate = data['completed_tasks'] / total * 100
        report.append(f"### {speaker}")
        report.append("")
        report.append(f"- **Total Tasks:** {total}")
        report.append(f"- **Completion Rate:** {completion_rate:.1f}%")
        report.append(f"- **Completed:** {data['completed_tasks']}")
        report.append(f"- **Pending:** {data['uncompleted_tasks']}")
        
        # Upcoming due dates
        if data['upcoming_due_dates']:
            report.append("- **Upcoming Due Dates:**")
            sorted_dates = sorted(data['upcoming_due_dates'])
            for date_str in sorted_dates[:3]:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    days_until = (date_obj - datetime.now()).days
                    if days_until < 0:
                        status = "OVERDUE"
                    elif days_until == 0:
                        status = "DUE TODAY"
                    elif days_until <= 3:
                        status = f"Due in {days_until} days"
                    else:
                        status = f"Due in {days_until} days"
                    report.append(f"  - {date_str[:10]} ({status})")
                except:
                    report.append(f"  - {date_str[:10]}")
        
        # Recent cards
        if data['cards']:
            report.append("- **Assigned Cards:**")
            pending_cards = [c for c in data['cards'] if c['status'] == 'incomplete'][:3]
            for card in pending_cards:
                due_info = f" (Due: {card['due_date'][:10]})" if card['due_date'] else ""
                report.append(f"  - [{card['card_name']}]({card['url']}){due_info}")
        
        report.append("")
    
    # Summary Statistics
    report.append("## 📈 Summary Statistics")
    report.append("")
    report.append(f"- **Total Active Speakers:** {len([s for s, d in speaker_data.items() if (d['completed_tasks'] + d['uncompleted_tasks']) > 0])}")
    report.append(f"- **Total Tasks:** {total_tasks}")
    report.append(f"- **Overall Completion Rate:** {sum(d['completed_tasks'] for d in speaker_data.values()) / total_tasks * 100:.1f}%")
    report.append(f"- **Busiest Speaker:** {sorted_speakers[0][0]} ({sorted_speakers[0][1]['completed_tasks'] + sorted_speakers[0][1]['uncompleted_tasks']} tasks)")
    
    # Best performer
    best = sorted([(s, d) for s, d in speaker_data.items() if (d['completed_tasks'] + d['uncompleted_tasks']) > 0],
                  key=lambda x: x[1]['completed_tasks'] / (x[1]['completed_tasks'] + x[1]['uncompleted_tasks']),
                  reverse=True)[0]
    report.append(f"- **Best Completion Rate:** {best[0]} ({best[1]['completed_tasks']}/{best[1]['completed_tasks'] + best[1]['uncompleted_tasks']} tasks)")
    report.append("")
    
    # Recommendations
    report.append("## 💡 Recommendations")
    report.append("")
    
    recommendations = []
    
    # Analyze workload distribution
    max_tasks = sorted_speakers[0][1]['completed_tasks'] + sorted_speakers[0][1]['uncompleted_tasks']
    min_tasks = min([d['completed_tasks'] + d['uncompleted_tasks'] for d in speaker_data.values() if (d['completed_tasks'] + d['uncompleted_tasks']) > 0])
    
    if max_tasks - min_tasks > 3:
        recommendations.append(f"Consider redistributing tasks from {sorted_speakers[0][0]} (who has {max_tasks} tasks) to speakers with lighter workloads.")
    
    # Check for overdue or urgent tasks
    urgent_speakers = []
    for speaker, data in speaker_data.items():
        if data['upcoming_due_dates']:
            next_due = min(data['upcoming_due_dates'])
            try:
                due_date = datetime.fromisoformat(next_due.replace('Z', '+00:00'))
                if (due_date - datetime.now()).days <= 2:
                    urgent_speakers.append(speaker)
            except:
                pass
    
    if urgent_speakers:
        recommendations.append(f"Urgent: Follow up with {', '.join(urgent_speakers)} about tasks due in the next 2 days.")
    
    # Low completion rates
    low_performers = []
    for speaker, data in speaker_data.items():
        total = data['completed_tasks'] + data['uncompleted_tasks']
        if total >= 3:
            completion_rate = data['completed_tasks'] / total * 100
            if completion_rate < 40:
                low_performers.append(speaker)
    
    if low_performers:
        recommendations.append(f"Consider providing additional support to {', '.join(low_performers)} who have completion rates below 40%.")
    
    if not recommendations:
        recommendations.append("Workload is well distributed. Keep up the good work!")
    
    for rec in recommendations:
        report.append(f"- {rec}")
    
    # Write report to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"Markdown report generated: '{output_file}'")
    return output_file

def main():
    # Load data
    data = load_trello_data()
    
    # Analyze data
    speaker_data = analyze_speaker_data(data)
    
    # Generate report
    report_file = generate_markdown_report(speaker_data)
    
    # Also print to console
    print("\n" + "="*50)
    print("QUICK SUMMARY:")
    print("="*50)
    
    # Show warnings
    warnings = []
    for speaker, data in speaker_data.items():
        total = data['completed_tasks'] + data['uncompleted_tasks']
        if total == 0:
            continue
        if data['uncompleted_tasks'] >= 5:
            warnings.append(f"WARNING: {speaker} has {data['uncompleted_tasks']} uncompleted tasks and {data['completed_tasks']} completed.")
    
    if warnings:
        for warning in warnings[:3]:
            print(f"• {warning}")
    
    # Show next due dates for busy speakers
    print("\nNext Due Dates:")
    for speaker, data in sorted(speaker_data.items(), key=lambda x: x[1]['uncompleted_tasks'], reverse=True)[:3]:
        if data['upcoming_due_dates']:
            next_due = min(data['upcoming_due_dates'])
            print(f"• {speaker}: {next_due[:10]}")

if __name__ == "__main__":
    main()
