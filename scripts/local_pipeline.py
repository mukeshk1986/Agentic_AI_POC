import sqlite3
import os
import re
import csv

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DDL_DIR = os.path.join(os.path.dirname(__file__), 'ddl')
DB_PATH = 'gap_suspecting.db'

def setup_database():
    """Initializes the SQLite connection."""
    con = sqlite3.connect(DB_PATH)
    return con

def parse_ddl(ddl_content):
    """
    Parses Databricks DDL and converts it to SQLite compatible SQL.
    """
    # Remove placeholders
    sql = re.sub(r'\$\{catalog\}\.\$\{schema_[^}]+\}\.', '', ddl_content)
    
    # Remove USING DELTA and PARTITIONED BY clauses
    sql = re.sub(r'USING\s+DELTA[^;]*;', ';', sql, flags=re.IGNORECASE | re.DOTALL)
    
    # Split by statement
    statements = sql.split(';')
    cleaned_statements = []
    
    for stmt in statements:
        if not stmt.strip():
            continue
            
        # Remove PARTITIONED BY (...)
        stmt = re.sub(r'PARTITIONED\s+BY\s*\([^)]+\)', '', stmt, flags=re.IGNORECASE)
        
        # Remove USING DELTA
        stmt = re.sub(r'USING\s+DELTA', '', stmt, flags=re.IGNORECASE)
        
        # Remove COMMENT '...'
        stmt = re.sub(r"COMMENT\s+'[^']*'", "", stmt, flags=re.IGNORECASE)
        
        # Remove GENERATED ALWAYS AS IDENTITY ...
        stmt = re.sub(r"GENERATED\s+ALWAYS\s+AS\s+IDENTITY\s*\([^)]+\)", "PRIMARY KEY AUTOINCREMENT", stmt, flags=re.IGNORECASE)
        
        # Type conversions
        stmt = re.sub(r'\bSTRING\b', 'TEXT', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bVARCHAR\(\d+\)', 'TEXT', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bCHAR\(\d+\)', 'TEXT', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bINT\b', 'INTEGER', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bSMALLINT\b', 'INTEGER', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bBIGINT\b', 'INTEGER', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bDECIMAL\(\d+,\d+\)', 'NUMERIC', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bDOUBLE\b', 'REAL', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bTIMESTAMP\b', 'TEXT', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bDATE\b', 'TEXT', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'\bBOOLEAN\b', 'INTEGER', stmt, flags=re.IGNORECASE)
        stmt = re.sub(r'ARRAY\s*<[^>]+>', 'TEXT', stmt, flags=re.IGNORECASE) # SQLite doesn't support arrays
        
        # Clean up extra whitespace
        stmt = stmt.strip()
        
        if stmt:
            cleaned_statements.append(stmt + ';')
            
    return cleaned_statements

def create_tables(con):
    """Reads DDL files and creates tables."""
    ddl_files = ['stage_tables.txt', 'ref_table.txt', 'trans_tables.txt']
    
    for ddl_file in ddl_files:
        path = os.path.join(DDL_DIR, ddl_file)
        if not os.path.exists(path):
            print(f"Warning: DDL file not found: {path}")
            continue
            
        with open(path, 'r') as f:
            content = f.read()
            
        statements = parse_ddl(content)
        for sql in statements:
            try:
                # print(f"Executing: {sql[:50]}...")
                con.execute(sql)
            except Exception as e:
                print(f"Error executing SQL: {e}")
                print(f"SQL: {sql}")

def load_data(con):
    """Loads data from text files into stage tables."""
    data_files = {
        'MEMBER_': 'stage_member',
        'FACILITY_HEADER_': 'stage_facility_header',
        'FACILITY_DETAIL_': 'stage_facility_detail',
        'FACILITY_DIAGNOSIS_': 'stage_facility_diag',
        'PROFESSIONAL_': 'stage_professional',
        'PROFESSIONAL_DIAGNOSIS_': 'stage_professional_diag',
        'PHARMACY_': 'stage_pharmacy',
        'PROVIDER_': 'stage_provider',
        'LOCATION_': 'stage_location'
    }
    
    for filename in os.listdir(DATA_DIR):
        table_name = None
        for prefix, table in data_files.items():
            if filename.startswith(prefix) and filename.endswith('.txt'):
                table_name = table
                break
        
        if table_name:
            print(f"Loading {filename} into {table_name}...")
            file_path = os.path.join(DATA_DIR, filename)
            
            # Get table columns
            cursor = con.cursor()
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                table_cols = [row[1] for row in cursor.fetchall()]
                
                if not table_cols:
                    print(f"Warning: Table {table_name} not found or has no columns.")
                    continue

                with open(file_path, 'r') as f:
                    # Check if file is empty
                    first_line = f.readline()
                    if not first_line:
                        print(f"Skipping empty file: {filename}")
                        continue
                    f.seek(0)
                    
                    reader = csv.DictReader(f, delimiter='|')
                    file_cols = reader.fieldnames
                    
                    if not file_cols:
                         print(f"Warning: No headers found in {filename}")
                         continue

                    # Find common columns
                    common_cols = [c for c in file_cols if c in table_cols]
                    
                    if not common_cols:
                        print(f"Warning: No common columns found for {filename} and {table_name}")
                        continue
                    
                    # Prepare INSERT statement
                    cols_str = ', '.join(common_cols)
                    placeholders = ', '.join(['?'] * len(common_cols))
                    sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
                    
                    rows_to_insert = []
                    for row in reader:
                        # Handle potential missing values or extra columns in row vs header
                        data = [row.get(c) for c in common_cols]
                        rows_to_insert.append(data)
                        
                    if rows_to_insert:
                        cursor.executemany(sql, rows_to_insert)
                        con.commit()
                        print(f"Loaded {len(rows_to_insert)} rows into {table_name}.")
                    else:
                        print(f"No rows found in {filename}.")
                        
            except Exception as e:
                print(f"Error loading {filename}: {e}")

from generate_ref_data import generate_ref_data

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    con = setup_database()
    create_tables(con)
    
    # Verify tables
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables created:")
    for t in tables:
        print(t[0])
        
    load_data(con)
    generate_ref_data(con, DATA_DIR)
        
    con.close()

if __name__ == "__main__":
    main()
