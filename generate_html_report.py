import json
from datetime import datetime
from collections import defaultdict
import pytz
from speaker_profiles import SPEAKER_PROFILES, CASTING_INSTRUCTIONS, get_speaker_profile

def load_trello_data(filename='trello_cards_detailed.json'):
    """Load the detailed Trello data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def get_german_time():
    """Get current time in German timezone (CET/CEST)."""
    german_tz = pytz.timezone('Europe/Berlin')
    return datetime.now(german_tz)

def generate_navigation_menu(current_page='workload'):
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

def analyze_speaker_data(data):
    """Analyze speaker workload and return structured data."""
    cards = data['cards_by_list'].get('Skripte zur Aufnahme', [])
    review_cards = data['cards_by_list'].get('In Review', [])
    done_cards = data['cards_by_list'].get('Fertig', [])
    
    speaker_data = defaultdict(lambda: {
        'completed_tasks': 0,
        'uncompleted_tasks': 0,
        'cards': [],
        'upcoming_due_dates': []
    })
    
    speaker_names = list(SPEAKER_PROFILES.keys())

    mentioned_speakers = set()
    for card in (review_cards + done_cards):
        haystack = f"{card.get('name', '')} {card.get('desc', '')}".lower()
        for name in speaker_names:
            if name.lower() in haystack:
                mentioned_speakers.add(name)
    
    for card in cards:
        card_name = card['name']
        card_due = card.get('due')
        card_url = card.get('shortUrl', '')
        
        for checklist in card.get('checklists', []):
            items = checklist.get('checkItems', [])
            
            for item in items:
                item_name = item.get('name', '')
                item_state = item.get('state', 'incomplete')
                
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

def generate_html_report(speaker_data, output_file='reports/speaker_workload_report.html'):
    """Generate a professional HTML report with Tailwind CSS."""
    
    german_time = get_german_time()
    total_tasks = sum(data['completed_tasks'] + data['uncompleted_tasks'] for data in speaker_data.values())
    sorted_speakers = sorted(speaker_data.items(), 
                           key=lambda x: x[1]['completed_tasks'] + x[1]['uncompleted_tasks'], 
                           reverse=True)
    
    # Generate warnings
    warnings = []
    for speaker, data in speaker_data.items():
        total = data['completed_tasks'] + data['uncompleted_tasks']
        if total == 0:
            continue
            
        completion_rate = data['completed_tasks'] / total * 100
        
        if data['uncompleted_tasks'] >= 5:
            warnings.append({
                'type': 'critical',
                'speaker': speaker,
                'message': f"{speaker} has {data['uncompleted_tasks']} uncompleted tasks and {data['completed_tasks']} completed."
            })
        elif completion_rate < 30 and total >= 3:
            warnings.append({
                'type': 'warning',
                'speaker': speaker,
                'message': f"{speaker} has a low completion rate of {completion_rate:.1f}% ({data['completed_tasks']}/{total} tasks)."
            })
        
        if data['upcoming_due_dates']:
            next_due = min(data['upcoming_due_dates'])
            try:
                due_date = datetime.fromisoformat(next_due.replace('Z', '+00:00'))
                days_until = (due_date - datetime.now()).days
                if days_until <= 3 and days_until >= 0:
                    warnings.append({
                        'type': 'urgent',
                        'speaker': speaker,
                        'message': f"{speaker} has a task due in {days_until} days ({next_due[:10]})."
                    })
            except:
                pass
    
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Speaker Workload Analysis Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
        <div class="max-w-7xl mx-auto">
            {generate_navigation_menu('workload')}
            
            <!-- Header -->
            <div class="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-lg shadow-lg p-8 mb-8 text-white">
                <h1 class="text-4xl font-bold mb-2">🎤 Speaker Workload Analysis</h1>
                <p class="text-blue-100">True Crime Video Dubs - Skripte zur Aufnahme</p>
                <p class="text-sm text-blue-200 mt-2">Generiert: {german_time.strftime('%d.%m.%Y %H:%M:%S')} CET</p>
            </div>

            <!-- Casting Instructions -->
            <div class="bg-blue-50 border-l-4 border-blue-500 rounded-lg p-6 mb-8">
                <h2 class="text-xl font-semibold text-blue-900 mb-3">📋 Casting-Anleitung</h2>
                <div class="text-blue-800 whitespace-pre-line">{CASTING_INSTRUCTIONS}</div>
            </div>

            <!-- Warnings Section -->
            <div class="mb-8">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">⚠️ Warnings</h2>
                <div class="space-y-3">
"""
    
    if warnings:
        for warning in warnings:
            if warning['type'] == 'critical':
                bg_color = 'bg-red-50'
                border_color = 'border-red-500'
                text_color = 'text-red-800'
                icon = '🚨'
            elif warning['type'] == 'urgent':
                bg_color = 'bg-orange-50'
                border_color = 'border-orange-500'
                text_color = 'text-orange-800'
                icon = '⏰'
            else:
                bg_color = 'bg-yellow-50'
                border_color = 'border-yellow-500'
                text_color = 'text-yellow-800'
                icon = '⚠️'
            
            html += f"""
                    <div class="{bg_color} border-l-4 {border_color} p-4 rounded">
                        <p class="{text_color} font-medium">{icon} {warning['message']}</p>
                    </div>
"""
    else:
        html += """
                    <div class="bg-green-50 border-l-4 border-green-500 p-4 rounded">
                        <p class="text-green-800 font-medium">✅ No critical warnings at this time.</p>
                    </div>
"""
    
    html += """
                </div>
            </div>

            <!-- Speaker Usage Overview Table -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden mb-8">
                <div class="px-6 py-4 bg-gray-800 text-white">
                    <h2 class="text-2xl font-bold">📊 Speaker Usage Overview</h2>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Speaker</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Tasks</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Completed</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pending</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Completion Rate</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Completion Rating</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">% of Total</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
"""
    
    for speaker, data in sorted_speakers:
        total = data['completed_tasks'] + data['uncompleted_tasks']
        completion_rate = (data['completed_tasks'] / total * 100) if total > 0 else 0
        workload_percentage = (total / total_tasks * 100) if total_tasks > 0 else 0

        profile = get_speaker_profile(speaker)
        is_unavailable = profile['availability'] != 'Available'
        row_classes = 'opacity-50' if is_unavailable else 'hover:bg-gray-50'
        speaker_label = f"{speaker} 😴" if is_unavailable else speaker
        speaker_text_class = 'text-gray-500' if is_unavailable else 'text-gray-900'
        completed_text_class = 'text-gray-500' if is_unavailable else 'text-green-600'
        pending_text_class = 'text-gray-500' if is_unavailable else 'text-orange-600'
        rate_text_class = 'text-gray-500' if is_unavailable else 'text-gray-700'
        progress_bg_class = 'bg-gray-400' if is_unavailable else 'bg-blue-600'
        
        if total == 0:
            status_badge = '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">—</span>'
        elif completion_rate == 100:
            status_badge = '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">✅ Excellent</span>'
        elif completion_rate >= 70:
            status_badge = '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">👍 Good</span>'
        elif completion_rate >= 40:
            status_badge = '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">⚠️ Fair</span>'
        else:
            status_badge = '<span class="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">🚨 Low</span>'
        
        html += f"""
                            <tr class="{row_classes}">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="text-sm font-medium {speaker_text_class}">{speaker_label}</div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-semibold">{total}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm {completed_text_class} font-medium">{data['completed_tasks']}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm {pending_text_class} font-medium">{data['uncompleted_tasks']}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                            <div class="{progress_bg_class} h-2 rounded-full" style="width: {completion_rate}%"></div>
                                        </div>
                                        <span class="text-sm {rate_text_class}">{completion_rate:.1f}%</span>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">{status_badge}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="text-sm text-gray-500">{workload_percentage:.1f}%</span>
                                </td>
                            </tr>
"""
    
    html += """
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Detailed Speaker Analysis -->
            <div class="space-y-6">
                <h2 class="text-2xl font-bold text-gray-800">📋 Detailed Speaker Analysis</h2>
"""
    
    for speaker, data in sorted_speakers:
        total = data['completed_tasks'] + data['uncompleted_tasks']
        if total == 0:
            continue
        
        completion_rate = data['completed_tasks'] / total * 100
        profile = get_speaker_profile(speaker)
        
        # Availability badge
        if profile['availability'] == 'Available':
            availability_badge = '<span class="px-3 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">✓ Verfügbar</span>'
        else:
            availability_badge = '<span class="px-3 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">✗ Nicht verfügbar</span>'
        
        html += f"""
                <div class="bg-white rounded-lg shadow-md overflow-hidden">
                    <div class="bg-gradient-to-r from-gray-700 to-gray-800 px-6 py-4">
                        <div class="flex items-center justify-between">
                            <h3 class="text-2xl font-bold text-white">{speaker}</h3>
                            {availability_badge}
                        </div>
                        <p class="text-gray-300 text-sm mt-1">{profile['role']}</p>
                    </div>
                    <div class="p-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                            <div>
                                <h4 class="text-sm font-semibold text-gray-500 uppercase mb-2">Workload Statistics</h4>
                                <div class="space-y-2">
                                    <div class="flex justify-between items-center">
                                        <span class="text-gray-700">Total Tasks:</span>
                                        <span class="font-bold text-gray-900">{total}</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-gray-700">Completion Rate:</span>
                                        <span class="font-bold text-blue-600">{completion_rate:.1f}%</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-gray-700">Completed:</span>
                                        <span class="font-bold text-green-600">{data['completed_tasks']}</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-gray-700">Pending:</span>
                                        <span class="font-bold text-orange-600">{data['uncompleted_tasks']}</span>
                                    </div>
                                </div>
                            </div>
                            <div>
                                <h4 class="text-sm font-semibold text-gray-500 uppercase mb-2">Voice Profile</h4>
                                <div class="space-y-2">
"""
        
        if profile['voice_characteristics']:
            html += f"""
                                    <div>
                                        <span class="text-xs font-semibold text-gray-500">Stimmcharakteristik:</span>
                                        <p class="text-sm text-gray-700 mt-1">{profile['voice_characteristics']}</p>
                                    </div>
"""
        
        if profile['casting_guidance']:
            html += f"""
                                    <div>
                                        <span class="text-xs font-semibold text-gray-500">Casting-Empfehlung:</span>
                                        <p class="text-sm text-gray-700 mt-1">{profile['casting_guidance']}</p>
                                    </div>
"""
        
        html += """
                                </div>
                            </div>
                        </div>
"""
        
        # Upcoming due dates
        if data['upcoming_due_dates']:
            html += """
                        <div class="mb-4">
                            <h4 class="text-sm font-semibold text-gray-500 uppercase mb-2">📅 Upcoming Due Dates</h4>
                            <div class="space-y-1">
"""
            sorted_dates = sorted(data['upcoming_due_dates'])[:3]
            for date_str in sorted_dates:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    days_until = (date_obj - datetime.now()).days
                    
                    if days_until < 0:
                        badge_color = 'bg-red-100 text-red-800'
                        status = 'OVERDUE'
                    elif days_until == 0:
                        badge_color = 'bg-orange-100 text-orange-800'
                        status = 'DUE TODAY'
                    elif days_until <= 3:
                        badge_color = 'bg-yellow-100 text-yellow-800'
                        status = f'Due in {days_until} days'
                    else:
                        badge_color = 'bg-blue-100 text-blue-800'
                        status = f'Due in {days_until} days'
                    
                    html += f"""
                                <div class="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
                                    <span class="text-sm text-gray-700">{date_str[:10]}</span>
                                    <span class="px-2 py-1 text-xs font-semibold rounded {badge_color}">{status}</span>
                                </div>
"""
                except:
                    html += f"""
                                <div class="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
                                    <span class="text-sm text-gray-700">{date_str[:10]}</span>
                                </div>
"""
            
            html += """
                            </div>
                        </div>
"""
        
        # Assigned cards
        if data['cards']:
            pending_cards = [c for c in data['cards'] if c['status'] == 'incomplete'][:5]
            if pending_cards:
                html += """
                        <div>
                            <h4 class="text-sm font-semibold text-gray-500 uppercase mb-2">📋 Pending Cards</h4>
                            <div class="space-y-2">
"""
                for card in pending_cards:
                    due_info = f" (Due: {card['due_date'][:10]})" if card['due_date'] else ""
                    html += f"""
                                <div class="flex items-start py-2 px-3 bg-gray-50 rounded hover:bg-gray-100">
                                    <span class="text-orange-500 mr-2">⏳</span>
                                    <a href="{card['url']}" target="_blank" class="text-sm text-blue-600 hover:text-blue-800 hover:underline flex-1">
                                        {card['card_name']}{due_info}
                                    </a>
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
    
    # Summary Statistics
    html += f"""
            </div>

            <!-- Summary Statistics -->
            <div class="bg-white rounded-lg shadow-lg p-6 mt-8">
                <h2 class="text-2xl font-bold text-gray-800 mb-4">📈 Summary Statistics</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div class="bg-blue-50 rounded-lg p-4">
                        <p class="text-sm text-blue-600 font-semibold">Active Speakers</p>
                        <p class="text-3xl font-bold text-blue-900">{len([s for s, d in speaker_data.items() if (d['completed_tasks'] + d['uncompleted_tasks']) > 0])}</p>
                    </div>
                    <div class="bg-green-50 rounded-lg p-4">
                        <p class="text-sm text-green-600 font-semibold">Total Tasks</p>
                        <p class="text-3xl font-bold text-green-900">{total_tasks}</p>
                    </div>
                    <div class="bg-purple-50 rounded-lg p-4">
                        <p class="text-sm text-purple-600 font-semibold">Overall Completion</p>
                        <p class="text-3xl font-bold text-purple-900">{sum(d['completed_tasks'] for d in speaker_data.values()) / total_tasks * 100:.1f}%</p>
                    </div>
                    <div class="bg-orange-50 rounded-lg p-4">
                        <p class="text-sm text-orange-600 font-semibold">Busiest Speaker</p>
                        <p class="text-2xl font-bold text-orange-900">{sorted_speakers[0][0]}</p>
                        <p class="text-sm text-orange-600">{sorted_speakers[0][1]['completed_tasks'] + sorted_speakers[0][1]['uncompleted_tasks']} tasks</p>
                    </div>
                </div>
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
    speaker_data = analyze_speaker_data(data)
    html_file = generate_html_report(speaker_data)
    
    print("\n" + "="*50)
    print("HTML REPORT GENERATED SUCCESSFULLY")
    print("="*50)
    print(f"Open '{html_file}' in your browser to view the report.")

if __name__ == "__main__":
    main()
