#!/usr/bin/env python3
import sqlite3
import os

def analyze_conflicts():
    # Connect to parliament_data.db
    conn = sqlite3.connect('parliament_data.db')
    cursor = conn.cursor()
    
    # Analyze exclusivity patterns
    print('=== CONFLICTS OF INTEREST ANALYSIS ===')
    print()
    
    # Total count and exclusivity breakdown
    cursor.execute('SELECT COUNT(*) FROM conflicts_of_interest')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM conflicts_of_interest WHERE exclusivity = ?', ('S',))
    exclusive = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM conflicts_of_interest WHERE exclusivity = ?', ('N',))
    non_exclusive = cursor.fetchone()[0]
    
    print(f'Total deputies with conflict data: {total}')
    print(f'Exclusive (S): {exclusive} ({exclusive/total*100:.1f}%)')
    print(f'Non-exclusive (N): {non_exclusive} ({non_exclusive/total*100:.1f}%)')
    print()
    
    # Marital status analysis
    print('=== MARITAL STATUS BREAKDOWN ===')
    cursor.execute('SELECT marital_status, COUNT(*) FROM conflicts_of_interest WHERE marital_status IS NOT NULL GROUP BY marital_status ORDER BY COUNT(*) DESC')
    marital_stats = cursor.fetchall()
    for status, count in marital_stats:
        print(f'{status}: {count} deputies')
    print()
    
    # Spouse analysis
    cursor.execute('SELECT COUNT(*) FROM conflicts_of_interest WHERE spouse_name IS NOT NULL AND spouse_name != ?', ('',))
    with_spouse = cursor.fetchone()[0]
    print(f'Deputies with spouse information: {with_spouse}')
    
    # DGF number analysis (professional registration)
    cursor.execute('SELECT COUNT(*) FROM conflicts_of_interest WHERE dgf_number IS NOT NULL AND dgf_number != ?', ('',))
    with_dgf = cursor.fetchone()[0]
    print(f'Deputies with DGF registration: {with_dgf}')
    print()
    
    # Show potential conflicts (non-exclusive deputies with details)
    print('=== DEPUTIES WITH POTENTIAL CONFLICTS (Non-Exclusive) ===')
    cursor.execute('''
        SELECT full_name, marital_status, spouse_name, dgf_number
        FROM conflicts_of_interest 
        WHERE exclusivity = ?
        ORDER BY full_name
        LIMIT 10
    ''', ('N',))
    conflicts = cursor.fetchall()
    for name, marital, spouse, dgf in conflicts:
        na_status = marital if marital else 'N/A'
        na_spouse = spouse if spouse else 'N/A'
        na_dgf = dgf if dgf else 'N/A'
        print(f'• {name}')
        print(f'  Status: {na_status}, Spouse: {na_spouse}, DGF: {na_dgf}')
    
    remaining = non_exclusive - 10
    if remaining > 0:
        print(f'... and {remaining} more non-exclusive deputies')
    
    print()
    print('=== KEY INSIGHTS ===')
    print(f'• {non_exclusive/total*100:.1f}% of deputies have potential conflicts (non-exclusive)')
    print(f'• {with_spouse} deputies declared spouse information')
    print(f'• {with_dgf} deputies have professional DGF registrations')
    print('• Non-exclusive status indicates deputies may have other professional activities')
    
    conn.close()

if __name__ == '__main__':
    analyze_conflicts()