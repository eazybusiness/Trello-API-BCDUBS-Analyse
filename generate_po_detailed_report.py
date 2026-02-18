#!/usr/bin/env python3
"""
Generate detailed Project Owner report by month
"""

import json
import sys
import os
import time
from datetime import datetime, timezone
from collections import defaultdict

# Import functions from the main report generator
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generate_completed_html import (
    load_trello_data, analyze_completed_projects, get_german_time,
    _parse_trello_datetime, _month_key, _month_label, _project_owner_rate,
    _classify_roles, _compute_rates, _compute_payment_entries,
    _parse_minutes_from_custom_field, _find_video_minutes_from_links,
    _load_video_length_cache, _save_video_length_cache
)

def generate_po_detailed_report(projects, output_file='reports/po_detailed_report.html'):
    """Generate a detailed Project Owner report by month."""
    
    german_time = get_german_time()
    
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video_length_cache.json')
    video_length_cache = _load_video_length_cache(cache_path)
    cache_dirty = False
    
    # Group projects by month and P.O.
    monthly_po_projects = defaultdict(lambda: defaultdict(list))
    
    for p in projects:
        # Only include projects with a P.O.
        po = (p.get('project_owner') or '').strip()
        if not po:
            continue
            
        # Use 'Abgenommen am' first, fallback to due_date
        date_field = p.get('abgenommen_am') or p.get('due_date', '')
        due_dt = _parse_trello_datetime(date_field)
        if due_dt is None:
            continue
        if due_dt < datetime(2026, 1, 15, tzinfo=timezone.utc):
            continue
            
        month_key = _month_key(due_dt)
        monthly_po_projects[month_key][po].append(p)
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Owner Detailed Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
        <div class="max-w-7xl mx-auto">
            
            <!-- Header -->
            <div class="bg-gradient-to-r from-purple-600 to-indigo-700 rounded-lg shadow-lg p-8 mb-8 text-white">
                <h1 class="text-4xl font-bold mb-2">💼 Project Owner Detailed Report</h1>
                <p class="text-purple-100">Monthly breakdown of Project Owner earnings</p>
                <p class="text-sm text-purple-200 mt-2">Generiert: {german_time.strftime('%d.%m.%Y %H:%M:%S')} CET</p>
            </div>

            <!-- Summary Statistics -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm text-gray-500 font-semibold">Total P.O.s</p>
                            <p class="text-3xl font-bold text-gray-900">{len(set(po for month_data in monthly_po_projects.values() for po in month_data.keys()))}</p>
                        </div>
                        <div class="bg-purple-100 rounded-full p-3">
                            <svg class="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                            </svg>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm text-gray-500 font-semibold">Total Projects</p>
                            <p class="text-3xl font-bold text-gray-900">{sum(len(po_projects) for month_data in monthly_po_projects.values() for po_projects in month_data.values())}</p>
                        </div>
                        <div class="bg-blue-100 rounded-full p-3">
                            <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                            </svg>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow-md p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm text-gray-500 font-semibold">Months Covered</p>
                            <p class="text-3xl font-bold text-gray-900">{len(monthly_po_projects)}</p>
                        </div>
                        <div class="bg-green-100 rounded-full p-3">
                            <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                            </svg>
                        </div>
                    </div>
                </div>
            </div>
"""

    # Generate monthly sections
    for month_key in sorted(monthly_po_projects.keys()):
        month_dt = datetime.fromisoformat(f"{month_key}-01T00:00:00+00:00")
        month_label = _month_label(month_dt)
        
        html += f"""
            <!-- {month_label} Section -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden mb-8">
                <div class="px-6 py-4 bg-purple-800 text-white">
                    <h2 class="text-2xl font-bold">📅 {month_label}</h2>
                </div>
                <div class="p-6">
"""
        
        # Process each P.O. for this month
        for po_name in sorted(monthly_po_projects[month_key].keys()):
            po_projects = monthly_po_projects[month_key][po_name]
            po_total = 0.0
            
            html += f"""
                    <div class="mb-8">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">👤 {po_name}</h3>
                        <div class="overflow-x-auto">
                            <table class="min-w-full divide-y divide-gray-200">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Project</th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rate ($/min)</th>
                                        <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Minutes</th>
                                        <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total ($)</th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white divide-y divide-gray-200">
"""
            
            # Process each project for this P.O.
            for p in sorted(po_projects, key=lambda x: x.get('abgenommen_am') or x.get('due_date', '') or ''):
                project_cache_key = p.get('id') or p.get('url') or p.get('name')
                cached_minutes = video_length_cache.get(project_cache_key) if project_cache_key else None
                minutes = cached_minutes
                
                # Use custom field 'minuten' first, fallback to Google Sheets
                if minutes is None:
                    custom_minutes = _parse_minutes_from_custom_field(p.get('minuten'))
                    if custom_minutes is not None:
                        minutes = custom_minutes
                        if project_cache_key:
                            video_length_cache[project_cache_key] = int(custom_minutes)
                            cache_dirty = True
                
                if minutes is None:
                    extracted_minutes = _find_video_minutes_from_links(p.get('google_docs_links', []))
                    minutes = extracted_minutes
                    if project_cache_key and extracted_minutes is not None:
                        video_length_cache[project_cache_key] = int(extracted_minutes)
                        cache_dirty = True
                
                # Calculate P.O. earnings
                if minutes is not None:
                    po_rate = _project_owner_rate(p)
                    po_amount = float(minutes) * float(po_rate)
                    po_total += po_amount
                    
                    # Determine if express
                    is_express = any('express' in label.lower() for label in p.get('labels', []))
                    rate_type = "Express" if is_express else "Normal"
                    
                    html += f"""
                                    <tr class="hover:bg-gray-50">
                                        <td class="px-4 py-3 text-sm font-medium text-gray-900">
                                            <div class="flex flex-col">
                                                <span>{p.get('name', '')}</span>
                                                <span class="text-xs text-gray-500">{rate_type}</span>
                                            </div>
                                        </td>
                                        <td class="px-4 py-3 text-sm text-gray-700">{po_rate:.2f}</td>
                                        <td class="px-4 py-3 text-sm text-gray-700 text-right">{minutes}</td>
                                        <td class="px-4 py-3 text-sm font-semibold text-gray-900 text-right">{po_amount:.2f}</td>
                                    </tr>
"""
                else:
                    html += f"""
                                    <tr class="hover:bg-gray-50 opacity-50">
                                        <td class="px-4 py-3 text-sm font-medium text-gray-900">
                                            <div class="flex flex-col">
                                                <span>{p.get('name', '')}</span>
                                                <span class="text-xs text-red-500">No minutes data</span>
                                            </div>
                                        </td>
                                        <td class="px-4 py-3 text-sm text-gray-700">—</td>
                                        <td class="px-4 py-3 text-sm text-gray-700 text-right">—</td>
                                        <td class="px-4 py-3 text-sm font-semibold text-gray-900 text-right">—</td>
                                    </tr>
"""
            
            html += f"""
                                </tbody>
                                <tfoot class="bg-gray-50">
                                    <tr>
                                        <td class="px-4 py-3 text-sm font-semibold text-gray-900" colspan="3">{po_name} Total</td>
                                        <td class="px-4 py-3 text-sm font-bold text-purple-600 text-right">{po_total:.2f}</td>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                    </div>
"""
        
        html += """
                </div>
            </div>
"""

    # Overall summary
    overall_totals = defaultdict(float)
    for month_key in monthly_po_projects:
        for po_name in monthly_po_projects[month_key]:
            for p in monthly_po_projects[month_key][po_name]:
                # Get minutes (reuse logic from above)
                project_cache_key = p.get('id') or p.get('url') or p.get('name')
                minutes = video_length_cache.get(project_cache_key) if project_cache_key else None
                
                if minutes is None:
                    custom_minutes = _parse_minutes_from_custom_field(p.get('minuten'))
                    if custom_minutes is not None:
                        minutes = custom_minutes
                
                if minutes is None:
                    minutes = _find_video_minutes_from_links(p.get('google_docs_links', []))
                
                if minutes is not None:
                    po_rate = _project_owner_rate(p)
                    po_amount = float(minutes) * float(po_rate)
                    overall_totals[po_name] += po_amount
    
    html += """
            <!-- Overall Summary -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden mb-8">
                <div class="px-6 py-4 bg-purple-800 text-white">
                    <h2 class="text-2xl font-bold">📊 Overall Summary</h2>
                </div>
                <div class="p-6">
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Project Owner</th>
                                    <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Earnings ($)</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
"""
    
    for po_name, total in sorted(overall_totals.items(), key=lambda x: x[1], reverse=True):
        html += f"""
                                <tr class="hover:bg-gray-50">
                                    <td class="px-4 py-3 text-sm font-medium text-gray-900">{po_name}</td>
                                    <td class="px-4 py-3 text-sm font-bold text-purple-600 text-right">{total:.2f}</td>
                                </tr>
"""
    
    grand_total = sum(overall_totals.values())
    html += f"""
                            </tbody>
                            <tfoot class="bg-gray-50">
                                <tr>
                                    <td class="px-4 py-3 text-sm font-bold text-gray-900">Grand Total</td>
                                    <td class="px-4 py-3 text-sm font-bold text-purple-600 text-right">{grand_total:.2f}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="text-center mt-8 text-gray-500 text-sm">
                <p>Generated by Trello API Client | {german_time.strftime('%d.%m.%Y %H:%M:%S')} CET</p>
                <p class="mt-1">P.O. rates: Normal ${2.25*0.9:.2f}/min | Express ${2.90*0.9:.2f}/min (90% of standard rates)</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    if cache_dirty:
        _save_video_length_cache(cache_path, video_length_cache)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Project Owner detailed report generated: '{output_file}'")
    return output_file

def main():
    """Main function."""
    data = load_trello_data()
    projects = analyze_completed_projects(data)
    html_file = generate_po_detailed_report(projects)
    
    print("\n" + "="*50)
    print("PROJECT OWNER DETAILED REPORT GENERATED")
    print("="*50)
    print(f"Open '{html_file}' in your browser to view the report.")

if __name__ == "__main__":
    main()
