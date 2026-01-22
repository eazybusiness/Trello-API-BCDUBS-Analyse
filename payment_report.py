import json
from datetime import datetime
from collections import defaultdict

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def analyze_projects_for_payment(data):
    """Analyze all projects with their participants for payment calculation."""
    
    # Get cards from both "Fertig" (completed) and "Skripte zur Aufnahme" (in progress)
    completed_cards = data['cards_by_list'].get('Fertig', [])
    in_progress_cards = data['cards_by_list'].get('Skripte zur Aufnahme', [])
    
    all_cards = completed_cards + in_progress_cards
    
    projects = []
    
    for card in all_cards:
        project = {
            'name': card['name'],
            'status': 'Completed' if card in completed_cards else 'In Progress',
            'url': card.get('shortUrl', ''),
            'due_date': card.get('due', ''),
            'participants': [],
            'labels': [label.get('name', '') for label in card.get('labels', [])],
            'completion_date': card.get('dateLastActivity', '') if card in completed_cards else None
        }
        
        # Extract all participants from members
        for member in card.get('members', []):
            participant = {
                'full_name': member.get('fullName', ''),
                'username': member.get('username', ''),
                'role': 'Speaker'  # Default role
            }
            
            # Determine role based on username or name patterns
            name = participant['full_name'].lower()
            username = participant['username'].lower()
            
            if 'lucki' in username or 'narrator' in name:
                participant['role'] = 'Narrator'
            elif 'chaos' in username or 'belli' in username or 'jade' in username or 'sira' in username:
                participant['role'] = 'Speaker (Female)'
            else:
                participant['role'] = 'Speaker (Male)'
            
            # Avoid duplicates
            if not any(p['username'] == participant['username'] for p in project['participants']):
                project['participants'].append(participant)
        
        # Also check checklists for additional participants
        for checklist in card.get('checklists', []):
            items = checklist.get('checkItems', [])
            for item in items:
                item_name = item.get('name', '')
                
                # Map common names to full names
                name_mapping = {
                    'Lucas': 'Lucas Jacobs',
                    'Nils': 'Nils',
                    'Chaos': 'Chaos',
                    'Marcel': 'Marcel',
                    'Holger': 'Holger Irrmisch',
                    'Marco': 'Marco',
                    'Martin': 'Martin Lindner',
                    'Drystan': 'Drystan',
                    'Belli': 'Belli',
                    'Sira': 'Sira',
                    'Jade': 'Jade Hagemann',
                    'Jessica': 'Jessica Nett'
                }
                
                for short_name, full_name in name_mapping.items():
                    if short_name.lower() in item_name.lower():
                        # Check if already in participants
                        if not any(p['full_name'] == full_name for p in project['participants']):
                            participant = {
                                'full_name': full_name,
                                'username': short_name.lower(),
                                'role': 'Speaker' if short_name not in ['Lucas'] else 'Narrator'
                            }
                            project['participants'].append(participant)
                        break
        
        projects.append(project)
    
    return projects

def generate_payment_report(projects, output_file='reports/payment_report.md'):
    """Generate a payment report showing project participants."""
    
    report = []
    report.append("# 💰 Payment Report - Project Participants")
    report.append("")
    report.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Total Projects:** {len(projects)}")
    report.append("")
    
    # Summary by person
    participant_summary = defaultdict(lambda: {
        'completed_projects': [],
        'in_progress_projects': [],
        'role': '',
        'total_count': 0
    })
    
    for project in projects:
        for participant in project['participants']:
            name = participant['full_name']
            participant_summary[name]['role'] = participant['role']
            participant_summary[name]['total_count'] += 1
            
            if project['status'] == 'Completed':
                participant_summary[name]['completed_projects'].append(project['name'])
            else:
                participant_summary[name]['in_progress_projects'].append(project['name'])
    
    # Participant Summary Table
    report.append("## 📊 Participant Summary")
    report.append("")
    report.append("| Participant | Role | Completed Projects | In Progress | Total |")
    report.append("|-------------|------|-------------------|-------------|-------|")
    
    for participant, data in sorted(participant_summary.items(), key=lambda x: x[1]['total_count'], reverse=True):
        completed = len(data['completed_projects'])
        in_progress = len(data['in_progress_projects'])
        total = data['total_count']
        report.append(f"| {participant} | {data['role']} | {completed} | {in_progress} | {total} |")
    
    report.append("")
    
    # Detailed Project Breakdown
    report.append("## 📋 Detailed Project Breakdown")
    report.append("")
    
    # Group by status
    completed_projects = [p for p in projects if p['status'] == 'Completed']
    in_progress_projects = [p for p in projects if p['status'] == 'In Progress']
    
    # Completed Projects
    report.append("### ✅ Completed Projects (Ready for Payment)")
    report.append("")
    
    for project in sorted(completed_projects, key=lambda x: x.get('completion_date', ''), reverse=True):
        report.append(f"#### {project['name']}")
        report.append("")
        
        if project['completion_date']:
            report.append(f"**Completed:** {project['completion_date'][:10]}")
        if project['due_date']:
            report.append(f"**Due Date:** {project['due_date'][:10]}")
        
        report.append("")
        report.append("**Participants to Pay:**")
        
        # Group by role
        narrators = [p for p in project['participants'] if 'Narrator' in p['role']]
        speakers_male = [p for p in project['participants'] if 'Speaker (Male)' in p['role']]
        speakers_female = [p for p in project['participants'] if 'Speaker (Female)' in p['role']]
        other_speakers = [p for p in project['participants'] if p['role'] == 'Speaker']
        
        if narrators:
            for narrator in narrators:
                report.append(f"- 🎙️ **Narrator:** {narrator['full_name']}")
        
        if speakers_male:
            report.append("- 🎭 **Male Speakers:**")
            for speaker in speakers_male:
                report.append(f"  - {speaker['full_name']}")
        
        if speakers_female:
            report.append("- 🎤 **Female Speakers:**")
            for speaker in speakers_female:
                report.append(f"  - {speaker['full_name']}")
        
        if other_speakers:
            report.append("- 🔊 **Speakers:**")
            for speaker in other_speakers:
                report.append(f"  - {speaker['full_name']}")
        
        report.append("")
        report.append(f"**Trello Link:** [{project['name']}]({project['url']})")
        report.append("")
        report.append("---")
        report.append("")
    
    # In Progress Projects
    if in_progress_projects:
        report.append("### ⏳ In Progress Projects (For Future Payment)")
        report.append("")
        
        for project in sorted(in_progress_projects, key=lambda x: x.get('due_date', '')):
            report.append(f"#### {project['name']}")
            report.append("")
            
            if project['due_date']:
                report.append(f"**Due Date:** {project['due_date'][:10]}")
            
            report.append("")
            report.append("**Current Participants:**")
            
            for participant in project['participants']:
                report.append(f"- {participant['full_name']} ({participant['role']})")
            
            report.append("")
            report.append(f"**Trello Link:** [{project['name']}]({project['url']})")
            report.append("")
            report.append("---")
            report.append("")
    
    # Payment Calculation Template
    report.append("## 💷 Payment Calculation Template")
    report.append("")
    report.append("Copy this table to calculate payments:")
    report.append("")
    report.append("| Participant | Role | Completed Projects | Rate/Project | Total Amount |")
    report.append("|-------------|------|-------------------|--------------|--------------|")
    
    for participant, data in sorted(participant_summary.items(), key=lambda x: x[1]['total_count'], reverse=True):
        if data['completed_projects']:  # Only show those with completed work
            report.append(f"| {participant} | {data['role']} | {len(data['completed_projects'])} |  |  |")
    
    report.append("")
    report.append("*Fill in the Rate/Project column and calculate Total Amount*")
    
    # Write report
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"Payment report generated: '{output_file}'")
    return output_file

def export_payment_to_csv(projects, filename='reports/payment_report.csv'):
    """Export payment data to CSV format."""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow([
            'Project Name',
            'Status',
            'Completion Date',
            'Participant Name',
            'Participant Role',
            'Participant Username',
            'Trello URL'
        ])
        
        # Data rows
        for project in projects:
            for participant in project['participants']:
                writer.writerow([
                    project['name'],
                    project['status'],
                    project.get('completion_date', '')[:10] if project.get('completion_date') else '',
                    participant['full_name'],
                    participant['role'],
                    participant['username'],
                    project['url']
                ])
    
    print(f"Payment data exported to CSV: '{filename}'")

def main():
    # Load data
    data = load_trello_data()
    
    # Analyze projects
    projects = analyze_projects_for_payment(data)
    
    # Generate reports
    md_file = generate_payment_report(projects)
    csv_file = export_payment_to_csv(projects)
    
    # Print summary
    print("\n" + "="*50)
    print("PAYMENT REPORT SUMMARY:")
    print("="*50)
    
    completed = [p for p in projects if p['status'] == 'Completed']
    in_progress = [p for p in projects if p['status'] == 'In Progress']
    
    print(f"Completed projects: {len(completed)}")
    print(f"In-progress projects: {len(in_progress)}")
    
    # Count participants
    all_participants = defaultdict(int)
    for project in completed:
        for participant in project['participants']:
            all_participants[participant['full_name']] += 1
    
    print(f"\nParticipants to pay (from completed projects):")
    for participant, count in sorted(all_participants.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {participant}: {count} projects")

if __name__ == "__main__":
    main()
