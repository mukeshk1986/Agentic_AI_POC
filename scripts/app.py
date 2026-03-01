import streamlit as st
import sys
import os
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.agents.supervisor import ClinicalSupervisor
import scripts.db_manager as db

st.set_page_config(page_title="Virtual Clinical Agent", layout="wide")

st.title("Virtual Clinical Agent POC")

# Sidebar
st.sidebar.header("Configuration")
if st.sidebar.button("Run Pipeline (ETL)"):
    with st.spinner("Running Data Generation and ETL..."):
        # We can call the scripts directly or via subprocess
        import scripts.generate_mock_data as gen
        gen.main()
        db.setup_db()
        db.load_data()
    st.sidebar.success("Pipeline Completed!")

# Initialize Agent
if "agent" not in st.session_state:
    st.session_state.agent = ClinicalSupervisor()

# Main Interface
tab1, tab2 = st.tabs(["Agent Chat", "Data Tracing"])

with tab1:
    st.subheader("Chat with the Clinical Agent")
    st.info("Try asking: 'Show me all gaps', 'Explain pharmacy gap logic', 'Show details for MEM_1001'")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("How can I help you?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = st.session_state.agent.process(prompt)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

with tab2:
    st.subheader("Data Tracing")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Members")
        try:
            conn = db.get_connection()
            df_members = pd.read_sql("SELECT * FROM members", conn)
            st.dataframe(df_members)
            conn.close()
        except Exception as e:
            st.error(f"Error loading members: {e}")

    with col2:
        st.markdown("### Identified Gaps")
        try:
            df_gaps = db.identify_gaps()
            st.dataframe(df_gaps)
        except Exception as e:
            st.error(f"Error loading gaps: {e}")

    st.markdown("### Claims Evidence")
    claim_type = st.selectbox("Select Claim Type", ["Pharmacy", "Medical", "Diagnosis"])
    
    try:
        conn = db.get_connection()
        if claim_type == "Pharmacy":
            df = pd.read_sql("SELECT * FROM pharmacy_claims", conn)
        elif claim_type == "Medical":
            df = pd.read_sql("SELECT * FROM medical_claims", conn)
        else:
            df = pd.read_sql("SELECT * FROM diagnosis_claims", conn)
        st.dataframe(df)
        conn.close()
    except Exception as e:
        st.error(f"Error loading claims: {e}")
