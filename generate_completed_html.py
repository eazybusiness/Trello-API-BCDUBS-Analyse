import json
import re
from datetime import datetime
from collections import defaultdict
import pytz

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def get_german_time():
    """Get current time in German timezone (CET/CEST)."""
    german_tz = pytz.timezone('Europe/Berlin')
    return datetime.now(german_tz)

def extract_google_docs_link(text):
    """Extract Google Docs/Sheets links from text."""
    patterns = [
        r'https://docs\.google\.com/[^\s\)]+',
        r'https://drive\.google\.com/[^\s\)]+',
    ]
    
    links = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        links.extend(matches)
    
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
        
        for member in card.get('members', []):
            project['members'].append({
                'name': member.get('fullName', ''),
                'username': member.get('username', ''),
                'avatar': member.get('avatarUrl', '')
            })
        
        if project['description']:
            project['google_docs_links'] = extract_google_docs_link(project['description'])
        
        for action in card.get('actions', []):
            if action.get('type') == 'commentCard':
                comment_text = action.get('data', {}).get('text', '')
                if comment_text:
                    comment_links = extract_google_docs_link(comment_text)
                    project['google_docs_links'].extend(comment_links)
        
        project['google_docs_links'] = list(set(project['google_docs_links']))
        projects.append(project)
    
    return projects

def generate_navigation_menu(current_page='completed'):
    """Generate navigation menu HTML."""
    workload_active = 'bg-blue-700 text-white' if current_page == 'workload' else 'text-blue-100 hover:bg-blue-600 hover:text-white'
    completed_active = 'bg-blue-700 text-white' if current_page == 'completed' else 'text-blue-100 hover:bg-blue-600 hover:text-white'
    
    return f"""
    <nav class="bg-gradient-to-r from-blue-600 to-indigo-700 shadow-lg mb-8">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex space-x-4 py-4">
                <a href="speaker_workload_report.html" class="{workload_active} px-4 py-2 rounded-md text-sm font-medium transition-colors">
                    🎤 Speaker Workload
                </a>
                <a href="completed_projects_report.html" class="{completed_active} px-4 py-2 rounded-md text-sm font-medium transition-colors">
                    ✅ Completed Projects
                </a>
            </div>
        </div>
    </nav>
"""

def generate_completed_html_report(projects, output_file='reports/completed_projects_report.html'):
    """Generate a professional HTML report for completed projects."""
    
    german_time = get_german_time()
    
    # Calculate statistics
    speaker_stats = defaultdict(lambda: {'count': 0, 'projects': []})
    for project in projects:
        for member in project['members']:
            speaker_name = member['name'].split()[0]
            speaker_stats[speaker_name]['count'] += 1
            speaker_stats[speaker_name]['projects'].append(project['name'])
    
    sorted_projects = sorted(projects, key=lambda x: x.get('last_activity', ''), reverse=True)
    
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Completed Projects Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
        <div class="max-w-7xl mx-auto">
            {generate_navigation_menu('completed')}
            
            <!-- Header -->
            <div class="bg-gradient-to-r from-green-600 to-emerald-700 rounded-lg shadow-lg p-8 mb-8 text-white">
                <h1 class="text-4xl font-bold mb-2">✅ Completed Projects Report</h1>
                <p class="text-green-100">True Crime Video Dubs - Fertig</p>
                <p class="text-sm text-green-200 mt-2">Generiert: {german_time.strftime('%d.%m.%Y %H:%M:%S')} CET</p>
            </div>

            <!-- Summary Statistics -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm text-gray-500 font-semibold">Total Projects</p>
                            <p class="text-3xl font-bold text-gray-900">{len(projects)}</p>
                        </div>
                        <div class="bg-green-100 rounded-full p-3">
                            <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm text-gray-500 font-semibold">Active Speakers</p>
                            <p class="text-3xl font-bold text-gray-900">{len(speaker_stats)}</p>
                        </div>
                        <div class="bg-blue-100 rounded-full p-3">
                            <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                            </svg>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm text-gray-500 font-semibold">With Documentation</p>
                            <p class="text-3xl font-bold text-gray-900">{len([p for p in projects if p['google_docs_links']])}</p>
                        </div>
                        <div class="bg-purple-100 rounded-full p-3">
                            <svg class="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                            </svg>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Speaker Contributions Table -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden mb-8">
                <div class="px-6 py-4 bg-gray-800 text-white">
                    <h2 class="text-2xl font-bold">📊 Projects by Speaker</h2>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Speaker</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Projects Completed</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Percentage</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
"""
    
    total_participations = sum(stats['count'] for stats in speaker_stats.values())
    
    for speaker, stats in sorted(speaker_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        percentage = (stats['count'] / total_participations * 100) if total_participations > 0 else 0
        
        html += f"""
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-medium text-gray-900">{speaker}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{stats['count']}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="w-24 bg-gray-200 rounded-full h-2 mr-2">
                                            <div class="bg-green-600 h-2 rounded-full" style="width: {percentage}%"></div>
                                        </div>
                                        <span class="text-sm text-gray-700">{percentage:.1f}%</span>
                                    </div>
                                </td>
                            </tr>
"""
    
    html += """
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Detailed Project List -->
            <div class="space-y-6">
                <h2 class="text-2xl font-bold text-gray-800">📋 Detailed Project List</h2>
"""
    
    for i, project in enumerate(sorted_projects, 1):
        # Determine card color based on labels
        if 'EXPRESS' in project['labels']:
            card_color = 'border-l-4 border-red-500'
        elif 'Budgettausch' in project['labels']:
            card_color = 'border-l-4 border-yellow-500'
        else:
            card_color = 'border-l-4 border-green-500'
        
        html += f"""
                <div class="bg-white rounded-lg shadow-md overflow-hidden {card_color}">
                    <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
                        <div class="flex items-center justify-between">
                            <h3 class="text-xl font-bold text-gray-900">{i}. {project['name']}</h3>
"""
        
        if project['labels']:
            html += '<div class="flex gap-2">'
            for label in project['labels']:
                if label == 'EXPRESS':
                    badge_color = 'bg-red-100 text-red-800'
                elif label == 'Budgettausch':
                    badge_color = 'bg-yellow-100 text-yellow-800'
                else:
                    badge_color = 'bg-blue-100 text-blue-800'
                html += f'<span class="px-2 py-1 text-xs font-semibold rounded {badge_color}">{label}</span>'
            html += '</div>'
        
        html += """
                        </div>
                    </div>
                    <div class="p-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                            <div>
"""
        
        if project['due_date']:
            html += f"""
                                <div class="mb-2">
                                    <span class="text-sm font-semibold text-gray-500">Due Date:</span>
                                    <span class="text-sm text-gray-700 ml-2">{project['due_date'][:10]}</span>
                                </div>
"""
        
        if project['last_activity']:
            html += f"""
                                <div class="mb-2">
                                    <span class="text-sm font-semibold text-gray-500">Last Activity:</span>
                                    <span class="text-sm text-gray-700 ml-2">{project['last_activity'][:10]}</span>
                                </div>
"""
        
        html += """
                            </div>
                            <div>
"""
        
        if project['members']:
            html += """
                                <div>
                                    <span class="text-sm font-semibold text-gray-500">Team Members:</span>
                                    <div class="mt-2 flex flex-wrap gap-2">
"""
            for member in project['members']:
                html += f"""
                                        <span class="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                                            {member['name']}
                                        </span>
"""
            html += """
                                    </div>
                                </div>
"""
        
        html += """
                            </div>
                        </div>
"""
        
        if project['google_docs_links']:
            html += """
                        <div class="mt-4 pt-4 border-t border-gray-200">
                            <h4 class="text-sm font-semibold text-gray-700 mb-3">📄 Google Docs/Links:</h4>
                            <div class="space-y-2">
"""
            for link in project['google_docs_links']:
                if 'docs.google.com' in link:
                    icon = '📝'
                    link_type = 'Document'
                    bg_color = 'bg-blue-50'
                    text_color = 'text-blue-700'
                elif 'sheets.google.com' in link or 'spreadsheets' in link:
                    icon = '📊'
                    link_type = 'Spreadsheet'
                    bg_color = 'bg-green-50'
                    text_color = 'text-green-700'
                elif 'drive.google.com' in link:
                    icon = '📁'
                    link_type = 'Drive Folder'
                    bg_color = 'bg-yellow-50'
                    text_color = 'text-yellow-700'
                else:
                    icon = '🔗'
                    link_type = 'Link'
                    bg_color = 'bg-gray-50'
                    text_color = 'text-gray-700'
                
                html += f"""
                                <a href="{link}" target="_blank" class="flex items-center p-3 {bg_color} rounded-lg hover:shadow-md transition-shadow">
                                    <span class="text-2xl mr-3">{icon}</span>
                                    <div class="flex-1 min-w-0">
                                        <p class="text-xs font-semibold {text_color} uppercase">{link_type}</p>
                                        <p class="text-sm {text_color} truncate">{link}</p>
                                    </div>
                                    <svg class="w-5 h-5 {text_color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                    </svg>
                                </a>
"""
            html += """
                            </div>
                        </div>
"""
        
        html += f"""
                        <div class="mt-4 pt-4 border-t border-gray-200">
                            <a href="{project['url']}" target="_blank" class="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 font-medium">
                                📋 View in Trello
                                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                </svg>
                            </a>
                        </div>
                    </div>
                </div>
"""
    
    html += f"""
            </div>

            <!-- Footer -->
            <div class="text-center mt-8 text-gray-500 text-sm">
                <p>Generated by Trello API Client | {german_time.strftime('%d.%m.%Y %H:%M:%S')} CET</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML report generated: '{output_file}'")
    return output_file

def main():
    data = load_trello_data()
    projects = analyze_completed_projects(data)
    html_file = generate_completed_html_report(projects)
    
    print("\n" + "="*50)
    print("COMPLETED PROJECTS HTML REPORT GENERATED")
    print("="*50)
    print(f"Total projects: {len(projects)}")
    print(f"Open '{html_file}' in your browser to view the report.")

if __name__ == "__main__":
    main()
