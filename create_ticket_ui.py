import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
from tools.redmine_ops import create_redmine_ticket, list_redmine_projects

# Load environment variables
load_dotenv(find_dotenv(), override=True)

st.set_page_config(page_title="Create Redmine Ticket", page_icon="🎫")

st.title("🎫 Create Redmine Ticket")

# Fetch projects for dropdown
with st.spinner("Fetching projects..."):
    projects = list_redmine_projects()

if not projects:
    st.error("Could not fetch projects. Please check your Redmine configuration in .env")
    st.stop()

# Create a mapping of Project Name -> ID
project_map = {p["name"]: p["id"] for p in projects}
project_names = list(project_map.keys())

with st.form("ticket_form"):
    project_name = st.selectbox("Project", options=project_names)
    subject = st.text_input("Subject", max_chars=80, help="Max 80 characters")
    description = st.text_area("Description", max_chars=3000, height=200, help="Max 3000 characters")
    
    submitted = st.form_submit_button("Create Ticket")

    if submitted:
        if not subject:
            st.error("Subject is required.")
        elif not description:
            st.error("Description is required.")
        else:
            project_id = project_map[project_name]
            with st.spinner("Creating ticket..."):
                result = create_redmine_ticket(str(project_id), subject, description)
            
            if "Created Redmine Issue" in result:
                st.success(result)
            else:
                st.error(result)
