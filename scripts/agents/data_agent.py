from scripts.agents.framework import Agent, Tool
import scripts.db_manager as db

def get_all_gaps():
    df = db.identify_gaps()
    if df.empty:
        return "No gaps found."
    return df.to_string()

def get_member_gaps(member_id):
    df = db.identify_gaps()
    member_gaps = df[df['MEMBER_ID'] == member_id]
    if member_gaps.empty:
        return f"No gaps found for {member_id}."
    return member_gaps.to_string()

def get_member_details(member_id):
    conn = db.get_connection()
    df = pd.read_sql(f"SELECT * FROM members WHERE MEMBER_ID = '{member_id}'", conn)
    conn.close()
    if df.empty:
        return f"Member {member_id} not found."
    return df.to_string()

tools = [
    Tool("get_all_gaps", get_all_gaps, "Get all gaps for all members"),
    Tool("get_member_gaps", get_member_gaps, "Get gaps for a specific member"),
    Tool("get_member_details", get_member_details, "Get details of a member")
]

class DataAgent(Agent):
    def __init__(self):
        super().__init__("DataAgent", tools, "I fetch data from the clinical database.")
    
    def process(self, user_input):
        import re
        # Check for Member ID first
        match = re.search(r"MEM_\d+", user_input)
        if match:
            member_id = match.group(0)
            if "gap" in user_input.lower():
                return self.tools["get_member_gaps"].run(member_id)
            else:
                return self.tools["get_member_details"].run(member_id)
        
        # Fallback to keyword search
        if "all gaps" in user_input.lower():
            return self.tools["get_all_gaps"].run()
        elif "member" in user_input.lower():
             return "Please specify a Member ID (e.g., MEM_1001)."
             
        return "I can help you find gaps or member details."
