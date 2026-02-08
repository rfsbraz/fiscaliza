#!/usr/bin/env python3
"""
Test script to verify video data in interventions
"""

import sqlite3
import json

def test_video_data():
    """Test video data availability in interventions"""
    
    print("TESTING VIDEO DATA IN INTERVENTIONS...")
    print("=" * 60)
    
    db_path = 'parlamento.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count total interventions
    cursor.execute("SELECT COUNT(*) FROM intervencoes")
    total_interventions = cursor.fetchone()[0]
    
    # Count interventions with video data
    cursor.execute("SELECT COUNT(*) FROM intervencoes WHERE url_video IS NOT NULL")
    interventions_with_video = cursor.fetchone()[0]
    
    # Count modern video URLs
    cursor.execute("SELECT COUNT(*) FROM intervencoes WHERE url_video LIKE 'https://av.parlamento.pt/videos/%'")
    modern_video_urls = cursor.fetchone()[0]
    
    # Count thumbnails
    cursor.execute("SELECT COUNT(*) FROM intervencoes WHERE thumbnail_url IS NOT NULL")
    interventions_with_thumbnails = cursor.fetchone()[0]
    
    print(f"Total interventions: {total_interventions:,}")
    print(f"Interventions with video: {interventions_with_video:,} ({interventions_with_video/total_interventions*100:.1f}%)")
    print(f"Modern video URLs: {modern_video_urls:,}")
    print(f"Interventions with thumbnails: {interventions_with_thumbnails:,}")
    
    print("\nSample modern interventions with video:")
    print("-" * 60)
    
    cursor.execute("""
        SELECT id, tipo_intervencao, assunto, url_video, thumbnail_url, duracao_video
        FROM intervencoes 
        WHERE url_video LIKE 'https://av.parlamento.pt/videos/%'
        AND legislatura_id = (SELECT id FROM legislaturas WHERE numero = '17')
        LIMIT 3
    """)
    
    results = cursor.fetchall()
    
    for i, row in enumerate(results[:3], 1):
        print(f"\n{i}. Intervention ID: {row[0]}")
        print(f"   Type: {row[1]}")
        print(f"   Subject: {row[2][:60]}..." if row[2] and len(row[2]) > 60 else f"   Subject: {row[2]}")
        print(f"   Video URL: {row[3]}")
        print(f"   Thumbnail: {row[4]}")
        print(f"   Duration: {row[5]}")
    
    # Test API-like response format
    print("\nSample API response format:")
    print("-" * 60)
    
    cursor.execute("""
        SELECT tipo_intervencao, data_intervencao, sumario, resumo, fase_sessao,
               url_video, thumbnail_url, assunto, duracao_video
        FROM intervencoes 
        WHERE url_video LIKE 'https://av.parlamento.pt/videos/%'
        AND legislatura_id = (SELECT id FROM legislaturas WHERE numero = '17')
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if row:
        api_response = {
            'tipo': row[0],
            'data': row[1],
            'sumario': row[2],
            'resumo': row[3],
            'fase_sessao': row[4],
            'url_video': row[5],
            'thumbnail_url': row[6],
            'assunto': row[7],
            'duracao_video': row[8]
        }
        
        print(json.dumps(api_response, indent=2, ensure_ascii=False))
    
    conn.close()
    print("\nTEST COMPLETED!")

if __name__ == "__main__":
    test_video_data()