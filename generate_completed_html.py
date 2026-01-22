import json
import re
from datetime import datetime, timezone
from collections import defaultdict
import csv
import io
import math
import requests
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

def _normalize_person_key(name: str) -> str:
    return re.sub(r'\s+', ' ', (name or '').strip()).lower()

def _has_label(project, needle: str) -> bool:
    needle_l = needle.lower()
    return any(needle_l in (lbl or '').lower() for lbl in project.get('labels', []))

def _parse_trello_datetime(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None

def _is_due_after_cutoff(project, cutoff_date_yyyy_mm_dd: str) -> bool:
    due_dt = _parse_trello_datetime(project.get('due_date', ''))
    if due_dt is None:
        return False
    cutoff_dt = datetime.fromisoformat(f"{cutoff_date_yyyy_mm_dd}T00:00:00+00:00")
    return due_dt > cutoff_dt

def _role_map():
    return {
        'female': {
            'chaos',
            'siraverda',
            'sira',
            'jade hagemann',
            'jade',
            'belli',
            'jessica nett',
            'jessica',
        },
        'male': {
            'holger irrmisch',
            'holger',
            'martin lindner',
            'martin',
            'marcel',
            'nils sonnenberg',
            'nils',
            'drystan dominikus nolte',
            'drystan',
            'marco',
            'liberat schumann',
            'liberat',
        },
        'lucas_aliases': {
            'lucas',
            'lucas jacobs',
            'luckijacobs@live.de',
            'luckijacobs',
        },
    }

def _classify_roles(project):
    rm = _role_map()

    members = project.get('members', [])
    member_keys = []
    for m in members:
        full_name = m.get('name', '')
        username = m.get('username', '')
        member_keys.append(_normalize_person_key(full_name))
        member_keys.append(_normalize_person_key(username))

    has_lucas = any(k in rm['lucas_aliases'] for k in member_keys)
    has_holger = any(k in rm['male'] and 'holger' in k for k in member_keys)

    narrator_key = None
    if has_lucas:
        narrator_key = 'lucas'
    elif has_holger:
        narrator_key = 'holger'

    narrator_member_idx = None
    if narrator_key is not None:
        for i, m in enumerate(members):
            full_k = _normalize_person_key(m.get('name', ''))
            user_k = _normalize_person_key(m.get('username', ''))
            if narrator_key == 'lucas' and (full_k in rm['lucas_aliases'] or user_k in rm['lucas_aliases']):
                narrator_member_idx = i
                break
            if narrator_key == 'holger' and ('holger' in full_k or 'holger' in user_k):
                narrator_member_idx = i
                break

    roles = {}
    for i, m in enumerate(members):
        full_name = m.get('name', '')
        username = m.get('username', '')
        full_k = _normalize_person_key(full_name)
        user_k = _normalize_person_key(username)

        if narrator_member_idx is not None and i == narrator_member_idx:
            roles[full_name] = 'Narrator'
            continue

        gender_role = None
        if full_k in rm['female'] or user_k in rm['female']:
            gender_role = 'Speaker (Female)'
        elif full_k in rm['male'] or user_k in rm['male']:
            gender_role = 'Speaker (Male)'
        elif full_k in rm['lucas_aliases'] or user_k in rm['lucas_aliases']:
            gender_role = 'Speaker (Male)'
        else:
            gender_role = 'Speaker'

        roles[full_name] = gender_role

    return roles

def _google_sheet_to_csv_url(url: str) -> str | None:
    if not url:
        return None
    if 'docs.google.com/spreadsheets/' not in url:
        return None
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if not m:
        return None
    sheet_id = m.group(1)
    gid_match = re.search(r'[#&?]gid=([0-9]+)', url)
    gid = gid_match.group(1) if gid_match else '0'
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

def _extract_duration_minutes_from_sheet_csv(csv_text: str) -> int | None:
    if not csv_text:
        return None
    reader = csv.reader(io.StringIO(csv_text))
    last_val = None
    for row in reader:
        if len(row) >= 5:
            val = (row[4] or '').strip()
            if val:
                last_val = val
    if not last_val:
        return None

    m = re.match(r'^(\d{2}):(\d{2}):(\d{2})(?::(\d{2}))?$', last_val)
    if not m:
        return None

    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = int(m.group(3))

    total_minutes = hh * 60 + mm
    if ss >= 30:
        total_minutes += 1
    return total_minutes

def _find_video_minutes_from_links(links):
    for link in links or []:
        csv_url = _google_sheet_to_csv_url(link)
        if not csv_url:
            continue
        try:
            resp = requests.get(csv_url, timeout=15)
            if resp.status_code != 200:
                continue
            minutes = _extract_duration_minutes_from_sheet_csv(resp.text)
            if minutes is not None:
                return minutes
        except Exception:
            continue
    return None

def _compute_rates(project):
    express = _has_label(project, 'express')
    budgettausch = _has_label(project, 'budgettausch')

    narrator = 3.0
    male = 2.25
    female = 1.25

    if budgettausch:
        male, female = female, male

    if express:
        narrator += 0.25
        male += 0.25
        female += 0.25

    return {
        'Narrator': narrator,
        'Speaker (Male)': male,
        'Speaker (Female)': female,
        'Speaker': male,
    }

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
                                    <div class="mt-2 space-y-2">
"""
            roles_by_member = _classify_roles(project)
            for member in project['members']:
                role = roles_by_member.get(member['name'], 'Speaker')

                if role == 'Narrator':
                    bg_color = 'bg-purple-50'
                    text_color = 'text-purple-700'
                    border_color = 'border-purple-300'
                    role_icon = '🎙️'
                elif role == 'Speaker (Female)':
                    bg_color = 'bg-pink-50'
                    text_color = 'text-pink-700'
                    border_color = 'border-pink-300'
                    role_icon = '🎤'
                else:
                    bg_color = 'bg-blue-50'
                    text_color = 'text-blue-700'
                    border_color = 'border-blue-300'
                    role_icon = '🎭'
                
                html += f"""
                                        <div class="flex items-center justify-between px-3 py-2 {bg_color} border {border_color} rounded-lg">
                                            <div class="flex items-center gap-2">
                                                <span class="text-lg">{role_icon}</span>
                                                <span class="{text_color} font-medium text-sm">{member['name']}</span>
                                            </div>
                                            <span class="{text_color} text-xs font-semibold uppercase">{role}</span>
                                        </div>
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

        if _is_due_after_cutoff(project, '2026-01-15'):
            video_minutes = _find_video_minutes_from_links(project.get('google_docs_links', []))
            roles_by_member = _classify_roles(project)
            rates = _compute_rates(project)

            html += """
                        <div class="mt-4 pt-4 border-t border-gray-200">
                            <h4 class="text-sm font-semibold text-gray-700 mb-3">💰 Payment (Due after 15.01.2026)</h4>
"""

            if video_minutes is None:
                html += """
                            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-800">
                                Video length not found in linked Google Spreadsheet (column E).
                            </div>
                        </div>
"""
            else:
                total_amount = 0.0
                html += f"""
                            <div class="flex items-center justify-between mb-3">
                                <div class="text-sm text-gray-600">Video length (rounded): <span class=\"font-semibold text-gray-900\">{video_minutes} min</span></div>
                            </div>
                            <div class="overflow-x-auto">
                                <table class="min-w-full divide-y divide-gray-200">
                                    <thead class="bg-gray-50">
                                        <tr>
                                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Person</th>
                                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                                            <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Minutes</th>
                                            <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Rate ($/min)</th>
                                            <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Amount ($)</th>
                                        </tr>
                                    </thead>
                                    <tbody class="bg-white divide-y divide-gray-200">
"""

                for member in project.get('members', []):
                    person = member.get('name', '')
                    role = roles_by_member.get(person, 'Speaker')
                    rate = rates.get(role, rates['Speaker'])
                    amount = float(video_minutes) * float(rate)
                    total_amount += amount

                    html += f"""
                                        <tr class="hover:bg-gray-50">
                                            <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{person}</td>
                                            <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-700">{role}</td>
                                            <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-700 text-right">{video_minutes}</td>
                                            <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-700 text-right">{rate:.2f}</td>
                                            <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900 font-semibold text-right">{amount:.2f}</td>
                                        </tr>
"""

                html += f"""
                                    </tbody>
                                    <tfoot class="bg-gray-50">
                                        <tr>
                                            <td class="px-4 py-2 text-sm font-semibold text-gray-900" colspan="4">Total</td>
                                            <td class="px-4 py-2 text-sm font-bold text-gray-900 text-right">{total_amount:.2f}</td>
                                        </tr>
                                    </tfoot>
                                </table>
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
