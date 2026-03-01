import csv
import random
import os
from datetime import datetime, timedelta

# Paths
DATA_DIR = r"c:\Users\mukeshk\Git_Bash_Repos\popA\Agentic_AI_POC\scripts\data"
METADATA_FILE = os.path.join(DATA_DIR, "ref_method_metadata.csv")
OUTPUT_DIR = DATA_DIR # Generate in the same dir for now

# Output Files
MEMBERS_FILE = os.path.join(OUTPUT_DIR, "members.csv")
PHARMACY_FILE = os.path.join(OUTPUT_DIR, "pharmacy_claims.csv")
MEDICAL_FILE = os.path.join(OUTPUT_DIR, "medical_claims.csv")
DIAGNOSIS_FILE = os.path.join(OUTPUT_DIR, "diagnosis_claims.csv")

def load_metadata():
    rules = []
    with open(METADATA_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rules.append(row)
    return rules

def generate_date(days_back=365):
    start_date = datetime.now() - timedelta(days=days_back)
    random_days = random.randint(0, days_back)
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")

def main():
    print("Loading metadata...")
    rules = load_metadata()
    
    # Separate rules by Claim Type
    # Pharmacy Claims = NDC codes (regardless of Method ID, though usually Method 1)
    pharmacy_rules = [r for r in rules if 'NDC' in r['CLAIM_CD_TYPE']]
    
    # Medical Claims = CPT/HCPCS codes (Method 1 or 2)
    medical_rules = [r for r in rules if 'CPT' in r['CLAIM_CD_TYPE'] or 'HCPCS' in r['CLAIM_CD_TYPE']]

    members = []
    pharmacy_claims = []
    medical_claims = []
    diagnosis_claims = []

    member_id_counter = 1000

    # --- Scenario 1: Pharmacy Gap (Drug purchased, no diagnosis) ---
    # Pick a rule
    rule = pharmacy_rules[0] 
    drug_code = rule['CLAIM_CD'] # e.g., C9250
    # We need a diagnosis code that would satisfy this, but we won't add it.
    # The metadata doesn't explicitly link drug -> diagnosis in a simple column for "satisfaction", 
    # but the logic implies if they have the drug, they SHOULD have a condition.
    # For the "Gap" to exist, we just see the drug and NO matching diagnosis in history.
    
    member_id = f"MEM_{member_id_counter}"
    members.append([member_id, "John", "Doe", "1980-01-01", "M"])
    pharmacy_claims.append([member_id, drug_code, generate_date(30), "Pharmacy Gap Candidate"])
    # No diagnosis added -> GAP
    member_id_counter += 1

    # --- Scenario 2: Pharmacy No Gap (Drug purchased, diagnosis exists) ---
    member_id = f"MEM_{member_id_counter}"
    members.append([member_id, "Jane", "Smith", "1985-05-15", "F"])
    pharmacy_claims.append([member_id, drug_code, generate_date(30), "No Gap Candidate"])
    # Add a diagnosis. In a real scenario, we'd need the mapping. 
    # For this POC, let's assume we need to find *some* diagnosis. 
    # Actually, the gap logic usually checks if the *condition* (HCC) is present.
    # Let's add a dummy diagnosis that maps to the same CC_ID if possible, or just *any* diagnosis for now 
    # and we will refine the logic to check for specific missing diagnoses.
    # For now, let's add a diagnosis code "D123" and assume our logic will check for it.
    diagnosis_claims.append([member_id, "D123", generate_date(100), "Existing Diagnosis"])
    member_id_counter += 1

    # --- Scenario 3: Procedure Gap (Procedure done, no diagnosis in 180 days) ---
    rule = medical_rules[0]
    proc_code = rule['CLAIM_CD']
    
    member_id = f"MEM_{member_id_counter}"
    members.append([member_id, "Bob", "Jones", "1975-08-20", "M"])
    medical_claims.append([member_id, proc_code, generate_date(30), "Procedure Gap Candidate"])
    # No diagnosis in last 180 days -> GAP
    member_id_counter += 1

    # --- Scenario 4: Procedure No Gap (Procedure done, diagnosis exists recently) ---
    member_id = f"MEM_{member_id_counter}"
    members.append([member_id, "Alice", "Wonder", "1990-12-12", "F"])
    medical_claims.append([member_id, proc_code, generate_date(30), "No Gap Candidate"])
    diagnosis_claims.append([member_id, "D123", generate_date(30), "Recent Diagnosis"]) 
    member_id_counter += 1

    # Write Files
    print(f"Writing {len(members)} members...")
    with open(MEMBERS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["MEMBER_ID", "FIRST_NAME", "LAST_NAME", "DOB", "GENDER"])
        writer.writerows(members)

    print(f"Writing {len(pharmacy_claims)} pharmacy claims...")
    with open(PHARMACY_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["MEMBER_ID", "DRUG_CODE", "FILL_DATE", "NOTES"])
        writer.writerows(pharmacy_claims)

    print(f"Writing {len(medical_claims)} medical claims...")
    with open(MEDICAL_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["MEMBER_ID", "PROC_CODE", "SERVICE_DATE", "NOTES"])
        writer.writerows(medical_claims)
        
    print(f"Writing {len(diagnosis_claims)} diagnosis claims...")
    with open(DIAGNOSIS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["MEMBER_ID", "DIAG_CODE", "DIAG_DATE", "NOTES"])
        writer.writerows(diagnosis_claims)

    print("Data generation complete.")

if __name__ == "__main__":
    main()
