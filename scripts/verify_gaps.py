import sqlite3
import pandas as pd

DB_PATH = 'gap_suspecting.db'

def verify_member_gap(memb_id, suspected_hcc):
    con = sqlite3.connect(DB_PATH)
    print(f"\n{'='*50}")
    print(f"Verifying Gap for Member: {memb_id}, Suspected HCC: {suspected_hcc}")
    print(f"{'='*50}")

    # 1. Show Evidence of Suspect (The Qualifying Claim)
    print("\n1. EVIDENCE OF SUSPECT (Qualifying Claims):")
    print("   Looking for claims with CPT codes that map to the Suspected HCC in ref_method_metadata...")
    
    sql_suspect_evidence = f"""
    SELECT 
        p.CLM_ID_CD, 
        p.SERV_FROM_DT, 
        p.CPT_AND_HCPCS_CD, 
        r.CC_ID as MAPPED_HCC,
        'Professional' as TYPE
    FROM stage_professional p
    JOIN ref_method_metadata r ON p.CPT_AND_HCPCS_CD = r.CLAIM_CD AND r.CLAIM_TYPE = 'P'
    WHERE p.MEMB_ID_CD = '{memb_id}' AND r.CC_ID = {suspected_hcc}
    
    UNION ALL
    
    SELECT 
        d.CLM_ID_CD, 
        d.SERV_FROM_DT, 
        d.CPT_AND_HCPCS_CD, 
        r.CC_ID as MAPPED_HCC,
        'Facility' as TYPE
    FROM stage_facility_detail d
    JOIN stage_facility_header h ON d.CLM_ID_CD = h.CLM_ID_CD AND d.ADJ_SEQ_NUM = h.ADJ_SEQ_NUM
    JOIN ref_method_metadata r ON d.CPT_AND_HCPCS_CD = r.CLAIM_CD AND r.CLAIM_TYPE = 'F'
    WHERE h.MEMB_ID_CD = '{memb_id}' AND r.CC_ID = {suspected_hcc}
    """
    
    try:
        df_evidence = pd.read_sql(sql_suspect_evidence, con)
        if not df_evidence.empty:
            print(df_evidence.to_string(index=False))
        else:
            print("   NO EVIDENCE FOUND! (This shouldn't happen if the gap output is correct)")
    except Exception as e:
        print(f"   Error fetching evidence: {e}")

    # 2. Show Existing Diagnoses (Recapture Check)
    print("\n2. EXISTING DIAGNOSES & HCC MAPPINGS:")
    print("   Listing all diagnosis codes for this member and their mapped HCCs...")
    
    sql_diags = f"""
    SELECT 
        pd.CLM_ID_CD,
        pd.DIAG_CD,
        m."CMS-HCC-MODEL-CATEGORY-V24" as MAPPED_HCC
    FROM stage_professional_diag pd
    JOIN stage_professional p ON pd.CLM_ID_CD = p.CLM_ID_CD AND pd.ADJ_SEQ_NUM = p.ADJ_SEQ_NUM
    LEFT JOIN icd_hcc_mapping m ON pd.DIAG_CD = m.DIAGNOSISCODE
    WHERE p.MEMB_ID_CD = '{memb_id}'
    
    UNION ALL
    
    SELECT 
        fd.CLM_ID_CD,
        fd.DIAG_CD,
        m."CMS-HCC-MODEL-CATEGORY-V24" as MAPPED_HCC
    FROM stage_facility_diag fd
    JOIN stage_facility_header h ON fd.CLM_ID_CD = h.CLM_ID_CD AND fd.ADJ_SEQ_NUM = h.ADJ_SEQ_NUM
    LEFT JOIN icd_hcc_mapping m ON fd.DIAG_CD = m.DIAGNOSISCODE
    WHERE h.MEMB_ID_CD = '{memb_id}'
    """
    
    try:
        df_diags = pd.read_sql(sql_diags, con)
        if not df_diags.empty:
            print(df_diags.to_string(index=False))
            
            # Check if suspected HCC is present
            existing_hccs = df_diags['MAPPED_HCC'].dropna().astype(int).unique()
            if suspected_hcc in existing_hccs:
                print(f"\n   ❌ VERIFICATION FAILED: Suspected HCC {suspected_hcc} WAS found in diagnoses.")
            else:
                print(f"\n   ✅ VERIFICATION PASSED: Suspected HCC {suspected_hcc} is NOT present in diagnoses.")
        else:
            print("   No diagnoses found for this member.")
            print(f"\n   ✅ VERIFICATION PASSED: No diagnoses means the suspected HCC {suspected_hcc} is definitely missing.")
            
    except Exception as e:
        print(f"   Error fetching diagnoses: {e}")

    con.close()

if __name__ == "__main__":
    # Samples from gap_suspecting_output.csv
    verify_member_gap('88000000019', 22)
    verify_member_gap('51281KPDXK0LE', 51)
