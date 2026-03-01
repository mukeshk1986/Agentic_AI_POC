import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.agents.supervisor import ClinicalSupervisor

def test_bug():
    agent = ClinicalSupervisor()
    
    # User query that likely fails
    query = "Show me gaps for MEM_1001"
    print(f"Query: {query}")
    response = agent.process(query)
    print(f"Response: {response}")
    
    if "No gaps found" in response or "MEM_1001" in response:
        print("PASS: Agent understood the ID.")
    else:
        print("FAIL: Agent did not trigger member lookup.")

if __name__ == "__main__":
    test_bug()
