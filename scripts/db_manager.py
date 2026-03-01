import sqlite3
import pandas as pd
import os

DB_PATH = r"c:\Users\mukeshk\Git_Bash_Repos\popA\Agentic_AI_POC\scripts\clinical_poc.db"
DATA_DIR = r"c:\Users\mukeshk\Git_Bash_Repos\popA\Agentic_AI_POC\scripts\data"

def get_connection():
    return sqlite3.connect(DB_PATH)

def setup_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            MEMBER_ID TEXT PRIMARY KEY,
            FIRST_NAME TEXT,
            LAST_NAME TEXT,
            DOB TEXT,
            GENDER TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pharmacy_claims (
            MEMBER_ID TEXT,
            DRUG_CODE TEXT,
            FILL_DATE TEXT,
            NOTES TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_claims (
            MEMBER_ID TEXT,
            PROC_CODE TEXT,
            SERVICE_DATE TEXT,
            NOTES TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnosis_claims (
            MEMBER_ID TEXT,
            DIAG_CODE TEXT,
            DIAG_DATE TEXT,
            NOTES TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ref_metadata (
            METHOD_ID TEXT,
            CLAIM_CD TEXT,
            CLAIM_CD_TYPE TEXT,
            CC_ID TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Database setup complete.")

def load_data():
    conn = get_connection()
    
    # Load CSVs
    members_df = pd.read_csv(os.path.join(DATA_DIR, "members.csv"))
    members_df.to_sql("members", conn, if_exists="replace", index=False)

    pharmacy_df = pd.read_csv(os.path.join(DATA_DIR, "pharmacy_claims.csv"))
    pharmacy_df.to_sql("pharmacy_claims", conn, if_exists="replace", index=False)

    medical_df = pd.read_csv(os.path.join(DATA_DIR, "medical_claims.csv"))
    medical_df.to_sql("medical_claims", conn, if_exists="replace", index=False)

    diag_df = pd.read_csv(os.path.join(DATA_DIR, "diagnosis_claims.csv"))
    diag_df.to_sql("diagnosis_claims", conn, if_exists="replace", index=False)

    # Load Metadata (only relevant columns)
    meta_df = pd.read_csv(os.path.join(DATA_DIR, "ref_method_metadata.csv"))
    # Filter for relevant columns to avoid schema issues
    meta_df = meta_df[['METHOD_ID', 'CLAIM_CD', 'CLAIM_CD_TYPE', 'CC_ID']]
    meta_df.to_sql("ref_metadata", conn, if_exists="replace", index=False)

    conn.close()
    print("Data loaded.")

def identify_gaps():
    conn = get_connection()
    
    # Logic 1: Pharmacy Gaps
    # Find members who have a pharmacy claim (Method 1) 
    # BUT do not have a diagnosis claim that maps to the same CC_ID (or just any diagnosis for now as a proxy).
    # Since we don't have a full ICD->HCC map, we will assume that if they have NO diagnosis claims at all, it's a gap.
    # OR we can check if they have a diagnosis claim with 'D123' (our dummy "good" code).
    
    # Let's refine:
    # Gap = Has Drug Claim (linked to a CC_ID) AND NOT EXISTS (Diagnosis Claim linked to same CC_ID)
    # Since we lack the Diag->CC map, we will assume 'D123' maps to the CC_ID for the test case.
    
    # Logic 1: Pharmacy Gaps (NDC based)
    # Join pharmacy claims with metadata where Type is NDC
    pharmacy_gap_query = """
    SELECT 
        m.MEMBER_ID, 
        m.FIRST_NAME, 
        m.LAST_NAME, 
        'Pharmacy Gap' as GAP_TYPE,
        CAST(p.DRUG_CODE AS TEXT) as EVIDENCE,
        r.CC_ID,
        'Member has drug ' || p.DRUG_CODE || ' but no matching diagnosis.' as REASON
    FROM pharmacy_claims p
    JOIN members m ON p.MEMBER_ID = m.MEMBER_ID
    JOIN ref_metadata r ON p.DRUG_CODE = r.CLAIM_CD 
    WHERE r.CLAIM_CD_TYPE LIKE '%NDC%'
    AND NOT EXISTS (
        SELECT 1 FROM diagnosis_claims d 
        WHERE d.MEMBER_ID = p.MEMBER_ID
    )
    """

    # Logic 2: Procedure Gaps (CPT/HCPCS based)
    # Join medical claims with metadata where Type is CPT/HCPCS
    procedure_gap_query = """
    SELECT 
        m.MEMBER_ID, 
        m.FIRST_NAME, 
        m.LAST_NAME, 
        'Procedure Gap' as GAP_TYPE,
        CAST(mc.PROC_CODE AS TEXT) as EVIDENCE,
        r.CC_ID,
        'Member has procedure ' || mc.PROC_CODE || ' but no diagnosis in last 180 days.' as REASON
    FROM medical_claims mc
    JOIN members m ON mc.MEMBER_ID = m.MEMBER_ID
    JOIN ref_metadata r ON mc.PROC_CODE = r.CLAIM_CD 
    WHERE (r.CLAIM_CD_TYPE LIKE '%CPT%' OR r.CLAIM_CD_TYPE LIKE '%HCPCS%')
    AND NOT EXISTS (
        SELECT 1 FROM diagnosis_claims d 
        WHERE d.MEMBER_ID = mc.MEMBER_ID
        AND julianday(mc.SERVICE_DATE) - julianday(d.DIAG_DATE) BETWEEN 0 AND 180
    )
    """

    gaps = []
    
    print("Checking Pharmacy Gaps...")
    df_pharm = pd.read_sql(pharmacy_gap_query, conn)
    gaps.append(df_pharm)
    
    print("Checking Procedure Gaps...")
    df_proc = pd.read_sql(procedure_gap_query, conn)
    gaps.append(df_proc)

    all_gaps = pd.concat(gaps)
    conn.close()
    
    return all_gaps

if __name__ == "__main__":
    setup_db()
    load_data()
    gaps = identify_gaps()
    print("Found Gaps:")
    print(gaps)
