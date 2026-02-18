#!/usr/bin/env python3
"""
Generate monthly invoices with exact format matching
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
    _parse_trello_datetime, _month_key, _month_label,
    _classify_roles, _compute_rates, _compute_payment_entries,
    _parse_minutes_from_custom_field, _find_video_minutes_from_links,
    _load_video_length_cache, _save_video_length_cache
)

# Company information
COMPANY_INFO = {
    'name': 'Hiplus by Nils Peters',
    'business': 'Plácido Mendez 89, Santa Cruz, Bolivia',
    'contact_number': '+591 70827499',
    'tax_id': '295 - 430 - 028'
}

# Client information
CLIENT_INFO = {
    'name': 'Isabelle Wiermann',
    'business': 'Weitlingstraße 20, 39104 Magdeburg, Germany',
    'contact_number': '+49176-41860982',
    'tax_id': ''
}

# Bank information
BANK_INFO = {
    'account_name': 'Nils Peters',
    'account_number': 'DE98760300800280582575',
    'bic': 'CSDBDE71XXX',
    'currency': 'EUR'
}

def get_invoice_number(month_key):
    """Generate invoice number based on month."""
    year, month = month_key.split('-')
    month_num = int(month)
    # February = 2026-0002, March = 2026-0003, etc.
    invoice_num = month_num + 1  # January would be 2026-0001, February 2026-0002
    return f"{year}-{invoice_num:04d}"

def get_invoice_items_for_month(projects, month_key):
    """Get invoice items for a specific month - only NP's projects."""
    monthly_items = []
    
    for p in projects:
        # Only include projects where P.O. is NP
        po = (p.get('project_owner') or '').strip()
        if po != 'NP':
            continue
        
        # Use 'Abgenommen am' first, fallback to due_date
        date_field = p.get('abgenommen_am') or p.get('due_date', '')
        due_dt = _parse_trello_datetime(date_field)
        if due_dt is None:
            continue
        if due_dt < datetime(2026, 1, 15, tzinfo=timezone.utc):
            continue
            
        project_month_key = _month_key(due_dt)
        if project_month_key != month_key:
            continue
        
        # Get minutes
        project_cache_key = p.get('id') or p.get('url') or p.get('name')
        minutes = None
        
        # Use custom field 'minuten' first
        minutes_str = p.get('minuten')
        if minutes_str:
            minutes = _parse_minutes_from_custom_field(minutes_str)
        
        # Fallback to Google Sheets if needed
        if minutes is None:
            minutes = _find_video_minutes_from_links(p.get('google_docs_links', []))
        
        if minutes is not None:
            # Use P.O. rates with discounts already included
            is_express = any('express' in label.lower() for label in p.get('labels', []))
            po_rate = 2.61 if is_express else 2.02  # P.O. rates with 90% discount
            
            # Calculate total (rate * minutes)
            total = po_rate * minutes
            
            monthly_items.append({
                'project': p.get('name', ''),
                'minutes': minutes,
                'rate': po_rate,
                'total': total
            })
    
    return monthly_items

def generate_invoice_html(month_key, output_file='reports/invoices/'):
    """Generate invoice HTML for a specific month."""
    
    # Ensure output directory exists
    os.makedirs(output_file, exist_ok=True)
    
    data = load_trello_data()
    projects = analyze_completed_projects(data)
    
    # Get invoice items for this month
    items = get_invoice_items_for_month(projects, month_key)
    
    if not items:
        print(f"No items found for {month_key}")
        return None
    
    # Calculate totals
    subtotal = sum(item['total'] for item in items)
    tax_rate = 0.16  # 16% tax (included in subtotal)
    tax_amount = subtotal * tax_rate
    total = subtotal  # Tax is included, so total equals subtotal
    
    # Get invoice details
    invoice_number = get_invoice_number(month_key)
    invoice_date = get_german_time()
    # Calculate due date (14 days from invoice date)
    from datetime import timedelta
    due_date = invoice_date + timedelta(days=14)
    
    month_dt = datetime.fromisoformat(f"{month_key}-01T00:00:00+00:00")
    month_label = _month_label(month_dt)
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice {invoice_number}</title>
    <style>
        @page {{
            margin: 20mm;
            size: A4;
        }}
        
        body {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        
        .invoice {{
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .company-name {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .invoice-title {{
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        
        .invoice-info {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        
        .invoice-details {{
            text-align: left;
        }}
        
        .invoice-details div {{
            margin-bottom: 5px;
        }}
        
        .company-client {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }}
        
        .company-info, .client-info {{
            width: 48%;
        }}
        
        .info-section {{
            margin-bottom: 20px;
        }}
        
        .info-title {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .items-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        
        .items-table th,
        .items-table td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        
        .items-table th {{
            background-color: #f5f5f5;
            font-weight: bold;
        }}
        
        .items-table td:nth-child(2),
        .items-table td:nth-child(3),
        .items-table td:nth-child(4),
        .items-table td:nth-child(5),
        .items-table td:nth-child(6) {{
            text-align: right;
        }}
        
        .totals-section {{
            width: 300px;
            margin-left: auto;
            margin-bottom: 30px;
        }}
        
        .totals-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            padding: 5px 0;
        }}
        
        .totals-row.total {{
            border-top: 2px solid #333;
            font-weight: bold;
            padding-top: 10px;
        }}
        
        .payment-details {{
            margin-top: 30px;
            padding: 20px;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
        }}
        
        .payment-title {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .payment-info {{
            margin-bottom: 5px;
        }}
        
        @media print {{
            body {{
                font-size: 10px;
            }}
            
            .invoice {{
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="invoice">
        <!-- Header -->
        <div class="header">
            <div class="company-name">{COMPANY_INFO['name']}</div>
            <div class="invoice-title">INVOICE</div>
        </div>
        
        <!-- Invoice Information -->
        <div class="invoice-info">
            <div class="invoice-details">
                <div><strong>INVOICE NUMBER</strong></div>
                <div>{invoice_number}</div>
                <div><strong>INVOICE DATE</strong></div>
                <div>{invoice_date.strftime('%b %d, %Y')}</div>
                <div><strong>DUE DATE</strong></div>
                <div>14 days TT</div>
            </div>
        </div>
        
        <!-- Company and Client Information -->
        <div class="company-client">
            <div class="company-info">
                <div class="info-section">
                    <div class="info-title">COMPANY</div>
                    <div><strong>NAME</strong></div>
                    <div>{COMPANY_INFO['name']}</div>
                    <div><strong>BUSINESS</strong></div>
                    <div>{COMPANY_INFO['business']}</div>
                    <div><strong>ADDRESS</strong></div>
                    <div>Bolivia</div>
                    <div><strong>CONTACT NUMBER</strong></div>
                    <div>{COMPANY_INFO['contact_number']}</div>
                    <div><strong>TAX ID</strong></div>
                    <div>{COMPANY_INFO['tax_id']}</div>
                </div>
            </div>
            
            <div class="client-info">
                <div class="info-section">
                    <div class="info-title">BILLED TO</div>
                    <div><strong>NAME</strong></div>
                    <div>{CLIENT_INFO['name']}</div>
                    <div><strong>BUSINESS</strong></div>
                    <div>{CLIENT_INFO['business']}</div>
                    <div><strong>ADDRESS</strong></div>
                    <div>Germany</div>
                    <div><strong>CONTACT NUMBER</strong></div>
                    <div>{CLIENT_INFO['contact_number']}</div>
                    <div><strong>TAX ID</strong></div>
                    <div>{CLIENT_INFO['tax_id']}</div>
                </div>
            </div>
        </div>
        
        <!-- Items Table -->
        <table class="items-table">
            <thead>
                <tr>
                    <th>ITEM</th>
                    <th>RATE in USD</th>
                    <th>MINUTES</th>
                    <th>TOTAL</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Add items to table
    for item in items:
        html += f"""
                <tr>
                    <td>{item['project']}</td>
                    <td>${item['rate']:.2f}</td>
                    <td>{item['minutes']}</td>
                    <td>${item['total']:.2f}</td>
                </tr>
"""
    
    html += f"""
            </tbody>
        </table>
        
        <!-- Totals -->
        <div class="totals-section">
            <div class="totals-row">
                <div>SUBTOTAL (IN DOLLARS)</div>
                <div>${subtotal:.2f}</div>
            </div>
            <div class="totals-row">
                <div>TAX RATE (%)</div>
                <div>{tax_rate * 100:.0f}</div>
            </div>
            <div class="totals-row">
                <div>TAX (INCL.)</div>
                <div>${tax_amount:.2f}</div>
            </div>
            <div class="totals-row total">
                <div>TOTAL (IN DOLLARS)</div>
                <div>${total:.2f}</div>
            </div>
        </div>
        
        <!-- Payment Details -->
        <div class="payment-details">
            <div class="payment-title">PAYMENT DETAILS</div>
            <div class="payment-info">Please make payment within 7-14 business days from the invoice date using the following bank information:</div>
            <div class="payment-info"><strong>ACCOUNT NAME:</strong> {BANK_INFO['account_name']}</div>
            <div class="payment-info"><strong>ACCOUNT NUMBER:</strong> {BANK_INFO['account_number']}</div>
            <div class="payment-info"><strong>BIC:</strong> {BANK_INFO['bic']}</div>
            <div class="payment-info"><strong>CURRENCY:</strong> {BANK_INFO['currency']}</div>
        </div>
    </div>
</body>
</html>
"""
    
    # Save invoice
    filename = f"invoice_{month_key}.html"
    filepath = os.path.join(output_file, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Invoice generated: '{filepath}'")
    print(f"Invoice Number: {invoice_number}")
    print(f"Items: {len(items)}")
    print(f"Total: ${total:.2f}")
    
    return filepath

def generate_all_invoices():
    """Generate invoices for all available months."""
    data = load_trello_data()
    projects = analyze_completed_projects(data)
    
    # Get all available months
    months = set()
    for p in projects:
        date_field = p.get('abgenommen_am') or p.get('due_date', '')
        due_dt = _parse_trello_datetime(date_field)
        if due_dt is None:
            continue
        if due_dt < datetime(2026, 1, 15, tzinfo=timezone.utc):
            continue
        months.add(_month_key(due_dt))
    
    print(f"Found {len(months)} months to invoice")
    
    generated_files = []
    for month_key in sorted(months):
        print(f"\nGenerating invoice for {month_key}...")
        filepath = generate_invoice_html(month_key)
        if filepath:
            generated_files.append(filepath)
    
    print(f"\n{'='*50}")
    print("INVOICES GENERATED")
    print('='*50)
    print(f"Total invoices: {len(generated_files)}")
    for filepath in generated_files:
        print(f"  {filepath}")
    
    return generated_files

def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Generate invoice for specific month
        month_key = sys.argv[1]
        generate_invoice_html(month_key)
    else:
        # Generate all invoices
        generate_all_invoices()

if __name__ == "__main__":
    main()
