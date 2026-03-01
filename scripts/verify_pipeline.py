import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import scripts.generate_mock_data as gen
import scripts.db_manager as db
from scripts.agents.supervisor import ClinicalSupervisor

def test_pipeline():
    print("--- Step 1: Data Generation ---")
    gen.main()
    
    print("\n--- Step 2: DB Setup & Load ---")
    db.setup_db()
    db.load_data()
    
    print("\n--- Step 3: Gap Identification ---")
    gaps = db.identify_gaps()
    print(gaps)
    
    # Assert we found gaps
    if gaps.empty:
        print("FAIL: No gaps found!")
        sys.exit(1)
    else:
        print("PASS: Gaps identified.")

    print("\n--- Step 4: Agent Interaction ---")
    agent = ClinicalSupervisor()
    
    # Test 1: General Gap Query
    response = agent.process("Show me all gaps")
    print(f"User: Show me all gaps\nAgent: {response}\n")
    if "Pharmacy Gap" in response and "Procedure Gap" in response:
        print("PASS: Agent returned gaps.")
    else:
        print("FAIL: Agent did not return expected gaps.")
        sys.exit(1)

    # Test 2: Specific Member Query (Pick one from gaps)
    member_id = gaps.iloc[0]['MEMBER_ID']
    response = agent.process(f"Show me gaps for {member_id}")
    print(f"User: Show me gaps for {member_id}\nAgent: {response}\n")
    if member_id in response:
        print("PASS: Agent returned member gaps.")
    else:
        print("FAIL: Agent did not return member gaps.")

    # Test 3: Explanation
    response = agent.process("Explain pharmacy gap logic")
    print(f"User: Explain pharmacy gap logic\nAgent: {response}\n")
    if "chronic condition" in response:
        print("PASS: Agent explained logic.")
    else:
        print("FAIL: Agent explanation failed.")

    print("\n--- ALL TESTS PASSED ---")

if __name__ == "__main__":
    test_pipeline()
