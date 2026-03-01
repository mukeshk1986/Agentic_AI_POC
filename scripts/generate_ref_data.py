import sqlite3
import csv
import os

def generate_ref_data(con, data_dir):
    print("Generating synthetic reference data...")
    cursor = con.cursor()
    
    # 1. ref_method_metadata
    # We need to populate this with CPT/HCPCS codes found in the data files.
    # This table determines if a claim is a "qualifying claim" for risk adjustment.
    
    # Collect CPT codes from stage_professional and stage_facility_detail
    cpt_codes = set()
    
    try:
        cursor.execute("SELECT DISTINCT CPT_AND_HCPCS_CD FROM stage_professional")
        for row in cursor.fetchall():
            if row[0]: cpt_codes.add(row[0])
            
        cursor.execute("SELECT DISTINCT CPT_AND_HCPCS_CD FROM stage_facility_detail")
        for row in cursor.fetchall():
            if row[0]: cpt_codes.add(row[0])
    except Exception as e:
        print(f"Error fetching CPT codes: {e}")

    print(f"Found {len(cpt_codes)} unique CPT codes.")
    
    # Insert into ref_method_metadata
    # We'll assume all found CPT codes are qualifying for the POC.
    # We'll create entries for 'MA' program.
    
    sql_metadata = """
    INSERT INTO ref_method_metadata (
        METHOD_ID, PROGRAM, PROGRAM_MODEL, CLAIM_TYPE, ICD_VER, 
        CLAIM_CD_TYPE, CLAIM_CD, 
        EFFECTIVE_DATE, EXPIRATION_DATE, QUALIFIED_CLAIM, CC_ID
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    rows_metadata = []
    import random
    hccs = [19, 21, 22, 51, 52] # Dummy HCCs
    
    for code in cpt_codes:
        cc_id = random.choice(hccs)
        # Professional
        rows_metadata.append((1, 'MA', 'MA', 'P', '0', 'CPT', code, '2020-01-01', '2099-12-31', 1, cc_id))
        # Facility
        rows_metadata.append((1, 'MA', 'MA', 'F', '0', 'CPT', code, '2020-01-01', '2099-12-31', 1, cc_id))
        
    try:
        cursor.executemany(sql_metadata, rows_metadata)
        con.commit()
        print(f"Inserted {len(rows_metadata)} rows into ref_method_metadata.")
    except Exception as e:
        print(f"Error inserting into ref_method_metadata: {e}")

    # 2. icd_hcc_mapping
    # We need to map diagnosis codes to HCCs.
    # Collect diag codes from stage_professional_diag and stage_facility_diag
    
    diag_codes = set()
    try:
        cursor.execute("SELECT DISTINCT DIAG_CD FROM stage_professional_diag")
        for row in cursor.fetchall():
            if row[0]: diag_codes.add(row[0])
            
        cursor.execute("SELECT DISTINCT DIAG_CD FROM stage_facility_diag")
        for row in cursor.fetchall():
            if row[0]: diag_codes.add(row[0])
    except Exception as e:
        print(f"Error fetching DIAG codes: {e}")
        
    print(f"Found {len(diag_codes)} unique DIAG codes.")
    
    # Insert into icd_hcc_mapping
    # We'll assign random HCCs or just a default one for POC.
    # Columns: DIAGNOSISCODE, CMS-HCC-MODEL-CATEGORY-V24, etc.
    # We need to quote the column names with hyphens.
    
    sql_mapping = """
    INSERT INTO icd_hcc_mapping (
        DIAGNOSISCODE, 
        "CMS-HCC-MODEL-CATEGORY-V22", 
        "CMS-HCC-MODEL-CATEGORY-V24",
        "CMS-HCC-MODEL-CATEGORY-V28"
    ) VALUES (?, ?, ?, ?)
    """
    
    rows_mapping = []
    for code in diag_codes:
        # Assign a dummy HCC, e.g., 19 (Diabetes) or something.
        # Or just random between 1 and 100.
        hcc = 19 
        rows_mapping.append((code, hcc, hcc, hcc))
        
    try:
        cursor.executemany(sql_mapping, rows_mapping)
        con.commit()
        print(f"Inserted {len(rows_mapping)} rows into icd_hcc_mapping.")
    except Exception as e:
        print(f"Error inserting into icd_hcc_mapping: {e}")
        
