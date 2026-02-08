#!/usr/bin/env python3
"""
Script to create sample data for the Portuguese Parliament application
"""

import sqlite3
import os
from datetime import date

def create_sample_data():
    db_path = 'database/app.db'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database not found. Please run the schema creation first.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Insert sample parties
        parties = [
            ('PSD', 'Partido Social Democrata', '#FF6B00', 'Centro-direita'),
            ('PS', 'Partido Socialista', '#FF69B4', 'Centro-esquerda'),
            ('Chega', 'Chega', '#000080', 'Direita'),
            ('IL', 'Iniciativa Liberal', '#00BFFF', 'Liberal'),
            ('BE', 'Bloco de Esquerda', '#FF0000', 'Esquerda'),
            ('PCP', 'Partido Comunista Português', '#DC143C', 'Comunista'),
            ('CDS-PP', 'Centro Democrático Social', '#1E90FF', 'Centro-direita'),
            ('Livre', 'Livre', '#32CD32', 'Ecologista'),
            ('PAN', 'Pessoas-Animais-Natureza', '#228B22', 'Ambientalista'),
            ('JPP', 'Juntos Pelo Povo', '#FFD700', 'Regionalista')
        ]
        
        for sigla, designacao, cor, ideologia in parties:
            cursor.execute("""
                INSERT OR IGNORE INTO partidos (sigla, designacao_completa, cor_representativa, ideologia, ativo)
                VALUES (?, ?, ?, ?, 1)
            """, (sigla, designacao, cor, ideologia))
        
        # Insert sample electoral districts
        districts = [
            'Lisboa', 'Porto', 'Braga', 'Setúbal', 'Aveiro', 'Faro', 'Santarém',
            'Coimbra', 'Leiria', 'Viseu', 'Viana do Castelo', 'Vila Real',
            'Bragança', 'Guarda', 'Castelo Branco', 'Portalegre', 'Évora',
            'Beja', 'Açores', 'Madeira', 'Europa', 'Fora da Europa'
        ]
        
        for district in districts:
            cursor.execute("""
                INSERT OR IGNORE INTO circulos_eleitorais (designacao, tipo, regiao)
                VALUES (?, 'territorial', ?)
            """, (district, district))
        
        # Get party and district IDs
        cursor.execute("SELECT id, sigla FROM partidos")
        party_ids = {sigla: id for id, sigla in cursor.fetchall()}
        
        cursor.execute("SELECT id, designacao FROM circulos_eleitorais")
        district_ids = {designacao: id for id, designacao in cursor.fetchall()}
        
        cursor.execute("SELECT id FROM legislaturas WHERE numero = 'XVII'")
        legislatura_id = cursor.fetchone()[0]
        
        # Sample deputies with realistic Portuguese names
        sample_deputies = [
            # PSD deputies
            ('João Silva Santos', 'João Silva', 'M', '1975-03-15', 'Advogado', 'PSD', 'Lisboa'),
            ('Maria Fernanda Costa', 'Maria Costa', 'F', '1980-07-22', 'Economista', 'PSD', 'Porto'),
            ('António José Pereira', 'António Pereira', 'M', '1968-11-05', 'Engenheiro', 'PSD', 'Braga'),
            ('Ana Rita Sousa', 'Ana Sousa', 'F', '1985-02-18', 'Professora', 'PSD', 'Setúbal'),
            
            # PS deputies
            ('Carlos Manuel Rodrigues', 'Carlos Rodrigues', 'M', '1972-09-12', 'Médico', 'PS', 'Lisboa'),
            ('Teresa Maria Oliveira', 'Teresa Oliveira', 'F', '1978-04-30', 'Socióloga', 'PS', 'Porto'),
            ('Pedro Miguel Ferreira', 'Pedro Ferreira', 'M', '1983-12-08', 'Jornalista', 'PS', 'Coimbra'),
            
            # Chega deputies
            ('Ricardo João Mendes', 'Ricardo Mendes', 'M', '1981-06-25', 'Empresário', 'Chega', 'Faro'),
            ('Catarina Isabel Alves', 'Catarina Alves', 'F', '1976-10-14', 'Advogada', 'Chega', 'Santarém'),
            
            # IL deputies
            ('Miguel Ângelo Carvalho', 'Miguel Carvalho', 'M', '1987-01-03', 'Consultor', 'IL', 'Lisboa'),
            ('Joana Marques Pinto', 'Joana Pinto', 'F', '1990-08-17', 'Economista', 'IL', 'Porto'),
            
            # BE deputies
            ('Rui Pedro Marques', 'Rui Marques', 'M', '1979-05-09', 'Professor', 'BE', 'Lisboa'),
            
            # PCP deputies
            ('Manuela Santos Silva', 'Manuela Silva', 'F', '1965-03-27', 'Operária', 'PCP', 'Setúbal'),
            
            # Other parties
            ('Francisco Dias Costa', 'Francisco Costa', 'M', '1982-11-19', 'Biólogo', 'Livre', 'Lisboa'),
            ('Sandra Cristina Lopes', 'Sandra Lopes', 'F', '1988-07-04', 'Veterinária', 'PAN', 'Porto'),
        ]
        
        # Insert deputies and mandates
        for nome_completo, nome_principal, sexo, nascimento, profissao, partido, circulo in sample_deputies:
            # Insert deputy
            cursor.execute("""
                INSERT OR IGNORE INTO deputados 
                (nome_completo, nome_principal, sexo, data_nascimento, profissao, ativo)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (nome_completo, nome_principal, sexo, nascimento, profissao))
            
            # Get deputy ID
            cursor.execute("SELECT id FROM deputados WHERE nome_completo = ?", (nome_completo,))
            deputado_id = cursor.fetchone()[0]
            
            # Insert mandate
            cursor.execute("""
                INSERT OR IGNORE INTO mandatos 
                (deputado_id, partido_id, circulo_eleitoral_id, legislatura_id, data_inicio, ativo)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (deputado_id, party_ids[partido], district_ids[circulo], legislatura_id, '2025-06-03'))
        
        # Add some agenda events
        agenda_events = [
            ('Sessão Plenária', 'Debate sobre o Orçamento de Estado', '2025-07-29', '14:30', '18:00', 'Hemiciclo', 'Plenário'),
            ('Reunião de Comissão', 'Comissão de Assuntos Constitucionais', '2025-07-30', '10:00', '12:00', 'Sala 1', 'Comissão'),
            ('Audição Parlamentar', 'Ministro das Finanças', '2025-07-31', '15:00', '17:00', 'Sala 2', 'Audição'),
        ]
        
        for titulo, descricao, data, hora_inicio, hora_fim, local, tipo in agenda_events:
            cursor.execute("""
                INSERT OR IGNORE INTO agenda_eventos 
                (titulo, descricao, data_evento, hora_inicio, hora_fim, local, tipo_evento)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (titulo, descricao, data, hora_inicio, hora_fim, local, tipo))
        
        conn.commit()
        
        # Print statistics
        cursor.execute("SELECT COUNT(*) FROM deputados")
        total_deputados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM partidos")
        total_partidos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM circulos_eleitorais")
        total_circulos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mandatos")
        total_mandatos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM agenda_eventos")
        total_agenda = cursor.fetchone()[0]
        
        print(f"Sample data created successfully!")
        print(f"   - Deputies: {total_deputados}")
        print(f"   - Parties: {total_partidos}")
        print(f"   - Electoral Districts: {total_circulos}")
        print(f"   - Mandates: {total_mandatos}")
        print(f"   - Agenda Events: {total_agenda}")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    create_sample_data()