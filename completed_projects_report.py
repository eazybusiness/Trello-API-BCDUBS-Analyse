import json
from datetime import datetime
from collections import defaultdict

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def extract_google_docs_link(text):
    """Extract Google Docs/Sheets links from text."""
    import re
    
    # Pattern to match Google Docs/Sheets URLs
    patterns = [
        r'https://docs\.google\.com/[^\s\)]+',
        r'https://drive\.google\.com/[^\s\)]+',
    ]
    
    links = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        links.extend(matches)
    
    # Remove trailing punctuation
    cleaned_links = []
    for link in links:
        cleaned = link.rstrip('.,;:)]}')
        if cleaned not in cleaned_links:
            cleaned_links.append(cleaned)
    
    return cleaned_links

def analyze_completed_projects(data):
    """Analyze completed projects from the 'Fertig' list."""
    cards = data['cards_by_list'].get('Fertig', [])
    
    projects = []
    
    for card in cards:
        project = {
            'name': card['name'],
            'url': card.get('shortUrl', ''),
            'due_date': card.get('due', ''),
            'last_activity': card.get('dateLastActivity', ''),
            'description': card.get('desc', ''),
            'members': [],
            'google_docs_links': [],
            'labels': [label.get('name', '') for label in card.get('labels', [])]
        }
        
        # Extract members
        for member in card.get('members', []):
            project['members'].append({
                'name': member.get('fullName', ''),
                'username': member.get('username', ''),
                'avatar': member.get('avatarUrl', '')
            })
        
        # Extract Google Docs links from description
        if project['description']:
            project['google_docs_links'] = extract_google_docs_link(project['description'])
        
        # Also check comments for Google Docs links
        for action in card.get('actions', []):
            if action.get('type') == 'commentCard':
                comment_text = action.get('data', {}).get('text', '')
                if comment_text:
                    comment_links = extract_google_docs_link(comment_text)
                    project['google_docs_links'].extend(comment_links)
        
        # Remove duplicate links
        project['google_docs_links'] = list(set(project['google_docs_links']))
        
        projects.append(project)
    
    return projects

def generate_completed_report(projects, output_file='reports/completed_projects_report.md'):
    """Generate a Markdown report for completed projects."""
    
    report = []
    report.append("# ✅ Completed Projects Report")
    report.append("")
    report.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**List:** Fertig (Completed)")
    report.append(f"**Total Projects:** {len(projects)}")
    report.append("")
    
    # Summary by speaker
    speaker_stats = defaultdict(lambda: {'count': 0, 'projects': []})
    
    for project in projects:
        for member in project['members']:
            speaker_name = member['name'].split()[0]  # Use first name
            speaker_stats[speaker_name]['count'] += 1
            speaker_stats[speaker_name]['projects'].append(project['name'])
    
    # Speaker Summary Table
    report.append("## 📊 Projects by Speaker")
    report.append("")
    report.append("| Speaker | Projects Completed | Project List |")
    report.append("|---------|-------------------|--------------|")
    
    for speaker, stats in sorted(speaker_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        projects_list = ', '.join(stats['projects'][:3])
        if len(stats['projects']) > 3:
            projects_list += f" (and {len(stats['projects']) - 3} more)"
        report.append(f"| {speaker} | {stats['count']} | {projects_list} |")
    
    report.append("")
    
    # Detailed Project List
    report.append("## 📋 Detailed Project List")
    report.append("")
    
    # Sort projects by completion date (last activity)
    sorted_projects = sorted(projects, key=lambda x: x.get('last_activity', ''), reverse=True)
    
    for i, project in enumerate(sorted_projects, 1):
        report.append(f"### {i}. {project['name']}")
        report.append("")
        
        # Project metadata
        if project['due_date']:
            report.append(f"**Due Date:** {project['due_date'][:10]}")
        if project['last_activity']:
            report.append(f"**Last Activity:** {project['last_activity'][:10]}")
        
        # Members
        if project['members']:
            members_str = ', '.join([f"{m['name']}(@{m['username']})" for m in project['members']])
            report.append(f"**Team Members:** {members_str}")
        
        # Labels
        if project['labels']:
            labels_str = ', '.join(project['labels'])
            report.append(f"**Labels:** {labels_str}")
        
        # Google Docs Links
        if project['google_docs_links']:
            report.append("")
            report.append("**📄 Google Docs/Links:**")
            for link in project['google_docs_links']:
                # Determine link type
                if 'docs.google.com' in link:
                    link_type = "📝 Document"
                elif 'sheets.google.com' in link:
                    link_type = "📊 Spreadsheet"
                elif 'drive.google.com' in link:
                    link_type = "📁 Drive Folder"
                else:
                    link_type = "🔗 Link"
                
                report.append(f"- {link_type}: [{link}]({link})")
        
        # Trello URL
        report.append("")
        report.append(f"**📋 Trello Card:** [{project['name']}]({project['url']})")
        
        report.append("")
        report.append("---")
        report.append("")
    
    # Statistics
    report.append("## 📈 Statistics")
    report.append("")
    
    # Calculate stats
    total_projects = len(projects)
    total_speakers = len(speaker_stats)
    projects_with_docs = len([p for p in projects if p['google_docs_links']])
    
    report.append(f"- **Total Completed Projects:** {total_projects}")
    report.append(f"- **Active Speakers:** {total_speakers}")
    report.append(f"- **Projects with Documentation:** {projects_with_docs}/{total_projects} ({projects_with_docs/total_projects*100:.1f}%)")
    
    # Most productive speaker
    if speaker_stats:
        most_productive = max(speaker_stats.items(), key=lambda x: x[1]['count'])
        report.append(f"- **Most Productive Speaker:** {most_productive[0]} ({most_productive[1]['count']} projects)")
    
    # Recent activity
    recent_projects = [p for p in sorted_projects if p.get('last_activity')][:5]
    if recent_projects:
        report.append("")
        report.append("### Recently Completed (Last 5)")
        for project in recent_projects:
            report.append(f"- [{project['name']}]({project['url']}) - {project.get('last_activity', '')[:10]}")
    
    # Write report
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print(f"Completed projects report generated: '{output_file}'")
    return output_file

def export_completed_to_csv(projects, filename='reports/completed_projects.csv'):
    """Export completed projects to CSV format."""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow([
            'Project Name',
            'Trello URL',
            'Due Date',
            'Last Activity',
            'Team Members',
            'Labels',
            'Google Docs Links',
            'Number of Members'
        ])
        
        # Data rows
        for project in projects:
            members_str = '; '.join([f"{m['name']}(@{m['username']})" for m in project['members']])
            labels_str = '; '.join(project['labels'])
            docs_str = '; '.join(project['google_docs_links'])
            
            writer.writerow([
                project['name'],
                project['url'],
                project['due_date'][:10] if project['due_date'] else '',
                project['last_activity'][:10] if project['last_activity'] else '',
                members_str,
                labels_str,
                docs_str,
                len(project['members'])
            ])
    
    print(f"Completed projects exported to CSV: '{filename}'")

def main():
    # Load data
    data = load_trello_data()
    
    # Analyze completed projects
    projects = analyze_completed_projects(data)
    
    # Generate reports
    md_file = generate_completed_report(projects)
    csv_file = export_completed_to_csv(projects)
    
    # Print summary
    print("\n" + "="*50)
    print("COMPLETED PROJECTS SUMMARY:")
    print("="*50)
    print(f"Total completed projects: {len(projects)}")
    
    # Count by speaker
    speaker_counts = defaultdict(int)
    for project in projects:
        for member in project['members']:
            speaker_name = member['name'].split()[0]
            speaker_counts[speaker_name] += 1
    
    print("\nProjects by speaker:")
    for speaker, count in sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {speaker}: {count} projects")
    
    # Check for missing documentation
    missing_docs = [p for p in projects if not p['google_docs_links']]
    if missing_docs:
        print(f"\n⚠️  {len(missing_docs)} projects without Google Docs links")
        for project in missing_docs[:5]:
            print(f"      - {project['name']}")

if __name__ == "__main__":
    main()
