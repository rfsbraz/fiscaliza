"""
Deputy Linking Utilities
========================

Reusable functions for linking deputies across legislaturas.
Uses id_cadastro as the stable identifier across legislative periods.
This is the official Parliamentary registration ID from the Portuguese Assembly system.
"""

def get_deputy_unique_key(id_cadastro, nome_completo=None, data_nascimento=None):
    """
    Generate a unique key to identify the same person across legislaturas.
    
    Args:
        id_cadastro (int): Parliamentary registration ID (required stable identifier)
        nome_completo (str, optional): Full name of the deputy (kept for API compatibility)
        data_nascimento (str, optional): Birth date (kept for API compatibility)
    
    Returns:
        str: Unique key for grouping deputies
    """
    if not id_cadastro:
        raise ValueError("id_cadastro is required - all deputies must have a parliamentary registration ID")
    
    return f"id_cadastro:{id_cadastro}"

def group_deputies_by_person(deputies_list):
    """
    Group a list of deputy records by unique person using id_cadastro.
    
    Args:
        deputies_list (list): List of deputy dictionaries with id_cadastro (required)
    
    Returns:
        dict: Dictionary with unique_key -> list of deputy records
    """
    grouped = {}
    
    for deputy in deputies_list:
        id_cadastro = deputy.get('id_cadastro')
        if not id_cadastro:
            continue  # Skip deputies without id_cadastro (should not happen)
            
        unique_key = get_deputy_unique_key(id_cadastro)
        
        if unique_key not in grouped:
            grouped[unique_key] = []
        grouped[unique_key].append(deputy)
    
    return grouped

def get_most_recent_mandate(deputy_records):
    """
    Get the most recent mandate from a list of deputy records for the same person.
    
    Args:
        deputy_records (list): List of deputy records for the same person
    
    Returns:
        dict: Deputy record with the most recent mandate
    """
    if not deputy_records:
        return None
    
    # Sort by legislatura number (descending) to get most recent
    sorted_records = sorted(
        deputy_records,
        key=lambda x: x.get('legislatura_numero', 0),
        reverse=True
    )
    
    return sorted_records[0]

def enhance_deputy_with_career_info(deputy_record, all_records_for_person):
    """
    Enhance a deputy record with career information across all mandates.
    
    Args:
        deputy_record (dict): Main deputy record to enhance
        all_records_for_person (list): All records for this person
    
    Returns:
        dict: Enhanced deputy record with career statistics
    """
    enhanced = deputy_record.copy()
    
    # Calculate career statistics
    legislaturas_served = len(set(r.get('legislatura_numero') for r in all_records_for_person if r.get('legislatura_numero')))
    
    # Get all parties served with (for display)
    parties_served = list(set(
        f"{r.get('partido_sigla', 'N/A')}" 
        for r in all_records_for_person 
        if r.get('partido_sigla')
    ))
    
    # Get all circles represented
    circles_served = list(set(
        r.get('circulo', 'N/A') 
        for r in all_records_for_person 
        if r.get('circulo')
    ))
    
    # Determine if deputy is currently active
    has_active_mandate = any(
        record.get('legislatura_ativa') or record.get('mandato_ativo')
        for record in all_records_for_person
    )
    
    # Get the most recent completed mandate for inactive deputies
    latest_completed_mandate = None
    if not has_active_mandate:
        completed_mandates = [
            r for r in all_records_for_person 
            if r.get('mandato_fim') and not (r.get('legislatura_ativa') or r.get('mandato_ativo'))
        ]
        if completed_mandates:
            latest_completed = max(completed_mandates, 
                                 key=lambda x: x.get('legislatura_numero', 0))
            latest_completed_mandate = {
                'legislatura': latest_completed.get('legislatura_nome'),
                'periodo': f"{latest_completed.get('mandato_inicio', '')[:4]}-{latest_completed.get('mandato_fim', '')[:4]}" if latest_completed.get('mandato_inicio') and latest_completed.get('mandato_fim') else None
            }
    
    # Add career information
    enhanced['career_info'] = {
        'total_mandates': legislaturas_served,
        'parties_served': parties_served,
        'circles_served': circles_served,
        'first_mandate': min(r.get('legislatura_numero', float('inf')) for r in all_records_for_person),
        'latest_mandate': max(r.get('legislatura_numero', 0) for r in all_records_for_person),
        'is_multi_term': legislaturas_served > 1,
        'is_currently_active': has_active_mandate,
        'latest_completed_mandate': latest_completed_mandate
    }
    
    return enhanced

def get_unique_deputy_count_query():
    """
    Get the proper SQL query for counting unique deputies using id_cadastro.
    
    Returns:
        str: SQL query that counts unique deputies by id_cadastro
    """
    return "COUNT(DISTINCT id_cadastro)"

def get_unique_deputy_filter_query(table_alias="d"):
    """
    Get the proper SQL filter for unique deputy queries using id_cadastro.
    
    Args:
        table_alias (str): Alias for the deputados table in the query
    
    Returns:
        str: SQL field reference for unique deputy identification
    """
    return f"{table_alias}.id_cadastro"