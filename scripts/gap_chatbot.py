import sqlite3
import sys

DB_PATH = 'gap_suspecting.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_member_gaps(con, member_id):
    """
    Queries the database for gaps associated with a specific member.
    Re-uses the logic from run_gap_suspecting.py but filtered for one member.
    """
    
    # We can query the 'suspects' and 'recaptures' tables directly if they exist.
    # If not, we might need to recreate them or use the CSV.
    # Assuming 'suspects' and 'recaptures' tables were created by run_gap_suspecting.py
    
    sql = f"""
    SELECT DISTINCT
        s.SUSPECTED_HCC,
        s.SOURCE_TYPE,
        s.SOURCE_CLM_ID,
        s.SERV_FROM_DT
    FROM suspects s
    LEFT JOIN recaptures r ON s.MEMB_ID_CD = r.MEMB_ID_CD AND s.SUSPECTED_HCC = r.RECAPTURED_HCC
    WHERE s.MEMB_ID_CD = '{member_id}' AND r.RECAPTURED_HCC IS NULL
    """
    
    try:
        cursor = con.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        return f"Error: {e}"

def chat_loop():
    print("="*60)
    print("      CMS Gap Suspecting Chatbot")
    print("      Type 'exit' or 'quit' to stop.")
    print("="*60)
    
    con = get_connection()
    
    # Check if tables exist
    try:
        con.execute("SELECT 1 FROM suspects LIMIT 1")
    except sqlite3.OperationalError:
        print("Error: 'suspects' table not found. Please run 'run_gap_suspecting.py' first.")
        return

    while True:
        try:
            user_input = input("\nEnter Member ID: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
                
            gaps = get_member_gaps(con, user_input)
            
            if isinstance(gaps, str) and gaps.startswith("Error"):
                print(gaps)
                continue
                
            if not gaps:
                print(f"No gaps found for member {user_input}.")
            else:
                print(f"\nFound {len(gaps)} gap(s) for member {user_input}:")
                print(f"{'HCC':<10} | {'Source':<15} | {'Claim ID':<20} | {'Date':<12}")
                print("-" * 65)
                for row in gaps:
                    hcc, source, claim_id, date = row
                    print(f"{hcc:<10} | {source:<15} | {claim_id:<20} | {date:<12}")
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

    con.close()

if __name__ == "__main__":
    chat_loop()
