import sqlite3
import pandas as pd
import os

DB_PATH = 'gap_suspecting.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def run_gap_suspecting():
    con = get_connection()
    
    print("Running Gap Suspecting Logic...")
    
    # ==========================================
    # 1. Identify SUSPECTED Conditions (Method 1)
    # ==========================================
    # Logic: Member has a claim with a CPT/HCPCS/REV code that exists in ref_method_metadata.
    # The ref_method_metadata entry provides the 'CC_ID' (Suspected Condition).
    
    print("Identifying Suspected Conditions (Method 1)...")
    
    # Professional Claims -> Suspects
    sql_suspects_prof = """
    SELECT 
        p.MEMB_ID_CD,
        r.CC_ID as SUSPECTED_HCC,
        'Professional' as SOURCE_TYPE,
        p.CLM_ID_CD as SOURCE_CLM_ID,
        p.SERV_FROM_DT
    FROM stage_professional p
    JOIN ref_method_metadata r ON r.CLAIM_TYPE = 'P'
    WHERE 
        (r.CLAIM_CD_TYPE = 'CPT' AND p.CPT_AND_HCPCS_CD = r.CLAIM_CD)
        AND r.PROGRAM = 'MA'
    """
    
    # Facility Claims -> Suspects
    sql_suspects_fac = """
    SELECT 
        h.MEMB_ID_CD,
        r.CC_ID as SUSPECTED_HCC,
        'Facility' as SOURCE_TYPE,
        h.CLM_ID_CD as SOURCE_CLM_ID,
        d.SERV_FROM_DT
    FROM stage_facility_header h
    JOIN stage_facility_detail d ON h.CLM_ID_CD = d.CLM_ID_CD AND h.ADJ_SEQ_NUM = d.ADJ_SEQ_NUM
    JOIN ref_method_metadata r ON r.CLAIM_TYPE = 'F'
    WHERE 
        (
            (r.CLAIM_CD_TYPE = 'CPT' AND d.CPT_AND_HCPCS_CD = r.CLAIM_CD) OR
            (r.CLAIM_CD_TYPE = 'REV' AND d.REV_CD = r.CLAIM_CD)
        )
        AND r.PROGRAM = 'MA'
    """
    
    sql_create_suspects = f"""
    CREATE TABLE IF NOT EXISTS suspects AS
    {sql_suspects_prof}
    UNION ALL
    {sql_suspects_fac}
    """
    
    try:
        con.execute("DROP TABLE IF EXISTS suspects")
        con.execute(sql_create_suspects)
        print("Created suspects table.")
    except Exception as e:
        print(f"Error creating suspects table: {e}")

    # ==========================================
    # 2. Identify RECAPTURED Conditions
    # ==========================================
    # Logic: Member has a diagnosis code that maps to an HCC.
    
    print("Identifying Recaptured Conditions...")
    
    # Professional Diags
    sql_recapture_prof = """
    SELECT 
        p.MEMB_ID_CD,
        m."CMS-HCC-MODEL-CATEGORY-V24" as RECAPTURED_HCC
    FROM stage_professional p
    JOIN stage_professional_diag pd ON p.CLM_ID_CD = pd.CLM_ID_CD AND p.ADJ_SEQ_NUM = pd.ADJ_SEQ_NUM
    JOIN icd_hcc_mapping m ON pd.DIAG_CD = m.DIAGNOSISCODE
    """
    
    # Facility Diags
    sql_recapture_fac = """
    SELECT 
        h.MEMB_ID_CD,
        m."CMS-HCC-MODEL-CATEGORY-V24" as RECAPTURED_HCC
    FROM stage_facility_header h
    JOIN stage_facility_diag fd ON h.CLM_ID_CD = fd.CLM_ID_CD AND h.ADJ_SEQ_NUM = fd.ADJ_SEQ_NUM
    JOIN icd_hcc_mapping m ON fd.DIAG_CD = m.DIAGNOSISCODE
    """
    
    sql_create_recaptures = f"""
    CREATE TABLE IF NOT EXISTS recaptures AS
    {sql_recapture_prof}
    UNION ALL
    {sql_recapture_fac}
    """
    
    try:
        con.execute("DROP TABLE IF EXISTS recaptures")
        con.execute(sql_create_recaptures)
        print("Created recaptures table.")
    except Exception as e:
        print(f"Error creating recaptures table: {e}")

    # ==========================================
    # 3. Calculate GAPS
    # ==========================================
    # Logic: Gap = Suspect exists, but Recapture does not exist for the same Member + HCC.
    
    print("Calculating Gaps...")
    
    sql_gaps = """
    SELECT DISTINCT
        s.MEMB_ID_CD,
        s.SUSPECTED_HCC,
        s.SOURCE_TYPE as SUSPECT_SOURCE,
        s.SOURCE_CLM_ID,
        s.SERV_FROM_DT as SUSPECT_DATE
    FROM suspects s
    LEFT JOIN recaptures r ON s.MEMB_ID_CD = r.MEMB_ID_CD AND s.SUSPECTED_HCC = r.RECAPTURED_HCC
    WHERE r.RECAPTURED_HCC IS NULL
    """
    
    try:
        df_gaps = pd.read_sql(sql_gaps, con)
        print(f"Found {len(df_gaps)} gaps.")
        print(df_gaps.head())
        
        df_gaps.to_csv('gap_suspecting_output.csv', index=False)
        print("Results saved to gap_suspecting_output.csv")
        
    except Exception as e:
        print(f"Error calculating gaps: {e}")

    con.close()

if __name__ == "__main__":
    run_gap_suspecting()
