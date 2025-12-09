import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
from tools.redmine_ops import create_redmine_ticket, list_redmine_projects
from notification_agent import NotificationAgent

# Load environment variables
load_dotenv(find_dotenv(), override=True)

# Streamlit version compatibility for rerun
def rerun():
    """Compatible rerun function for different Streamlit versions"""
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

st.set_page_config(page_title="Create Redmine Ticket", page_icon="🎫", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .user-message {
        background-color: #e3f2fd;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        text-align: right;
    }
    .assistant-message {
        background-color: #f5f5f5;
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
    }
    .notification-preview {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        font-family: monospace;
        white-space: pre-wrap;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "ticket_form"  # ticket_form, notification_flow

if "notification_agent" not in st.session_state:
    st.session_state.notification_agent = NotificationAgent()
    st.session_state.messages = []
    st.session_state.notification_complete = False
    st.session_state.final_notification = None
    st.session_state.show_editable_table = False
    st.session_state.user_confirmed_data = False

# --- TICKET CREATION FORM ---
if st.session_state.page == "ticket_form":
    st.title("🎫 Create Redmine Ticket")
    st.markdown("*Fill out the form below to create a comprehensive work ticket*")

    # Fetch projects for dropdown
    with st.spinner("Fetching projects..."):
        projects = list_redmine_projects()

    if not projects:
        st.error("Could not fetch projects. Please check your Redmine configuration in .env")
        st.stop()

    # Create a mapping of Project Name -> ID
    project_map = {p["name"]: p["id"] for p in projects}
    project_names = sorted(list(project_map.keys()))

    # Two column layout
    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("ticket_form"):
            st.subheader("📋 Ticket Details")
            
            # Project selection
            # Default to "sCube Internal" if available
            default_index = 0
            if "sCube Internal" in project_names:
                default_index = project_names.index("sCube Internal")
                
            project_name = st.selectbox(
                "Project *",
                options=project_names,
                index=default_index,
                help="Select the project this ticket belongs to"
            )
            
            # Feature Type
            feature_type = st.selectbox(
                "Feature Type",
                options=[
                    "Automation", "Custom Fields", "Fees", "Flow", 
                    "Form Layout Back Office", "Form Layout Customer Portlet", 
                    "Inspections", "Notifications", "Reviews", 
                    "Sequence Numbering", "Submissions"
                ],
                help="Select the type of feature this ticket relates to"
            )
            
            # Subject (Renamed to Permit Application Type)
            subject = st.text_input(
                "Permit Application Type *",
                value="Street Closure - Notifications",
                max_chars=255,
                help="Type of permit application (max 255 characters)",
                placeholder="e.g., Street Closure"
            )
            
            # Description
            description = st.text_area(
                "Please paste your notifications in excel format *",
                value="Milestone\tSubject\tEmail\nSubmitted\tApplication [Application#] Has been submitted\tYour Application[Application#] at [Address] has been submitted and is pending review",
                max_chars=5000,
                height=300,
                help="Copy and paste your notifications table from Excel. Columns: Milestone, Subject, Email",
                placeholder="Milestone     Subject     Email\nSubmitted      Application [Application#] Has been submitted  Your Application[Application#]..."
            )
            
            st.divider()
            
            # Submit button
            submitted = st.form_submit_button("🔍 Validate Data", type="primary", use_container_width=True)
            
            if submitted:
                # Validation
                errors = []
                if not subject or len(subject.strip()) < 3:
                    errors.append("Permit Application Type must be at least 3 characters")
                if not description or len(description.strip()) < 10:
                    errors.append("Description must be at least 10 characters")
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    with st.spinner("Validating data..."):
                        # Store data for validation flow
                        st.session_state.ticket_data = {
                            "project_id": project_map[project_name],
                            "subject": subject.strip(),
                            "description": description.strip(),
                            "feature_type": feature_type
                        }
                        
                        # Transition to notification flow
                        st.session_state.page = "notification_flow"
                        st.session_state.ticket_description = description.strip()
                        
                        # Initialize notification agent with description
                        greeting = st.session_state.notification_agent.start_validation(description.strip())
                        st.session_state.messages = [{"role": "assistant", "content": greeting}]
                        rerun()

    with col2:
        st.subheader("💡 Tips")
        
        with st.expander("📝 Writing Good Descriptions", expanded=True):
            st.markdown("""
            **Include:**
            - What is the problem/need?
            - What should happen instead?
            - Steps to reproduce (for bugs)
            - Impact on users/business
            - Any error messages
            """)
        
        st.info(f"**{len(projects)} projects** available")

# --- NOTIFICATION FLOW ---
elif st.session_state.page == "notification_flow":
    st.title("📋 Notification Validator")
    
    # Check status and display appropriate header
    agent = st.session_state.notification_agent
    
    if agent.state == "complete":
        st.success("✅ Data Validated Successfully")
    elif agent.state == "review_needed":
        st.warning("⚠️ Review AI Modifications")
        st.markdown("*I made some changes to clean up your data. Please review them below.*")
    else:
        st.warning("⚠️ Formatting Issues Found")
        st.markdown("*I found some issues with the data format. Please review the errors below and make corrections.*")
    
    # Sidebar with status
    with st.sidebar:
        st.header("🔍 Validation Status")
        
        if agent.state == "complete":
            st.success("✅ Validation Passed")
            st.metric("Notifications", len(agent.notification_data))
        elif agent.state == "review_needed":
            st.warning("⚠️ Review Needed")
            st.metric("Modifications", len(agent.modifications_made))
        else:
            st.error("❌ Formatting Issues")
            st.metric("Issues Found", len(agent.validation_errors))
            
        st.divider()
        if st.button("🔙 Back to Ticket Form"):
            st.session_state.page = "ticket_form"
            rerun()

    # Main chat area
    chat_container = st.container()

    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="user-message">👤 {message["content"]}</div>', 
                           unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="assistant-message">🤖 {message["content"]}</div>', 
                           unsafe_allow_html=True)

    # Show editable table if validation succeeded (or pending review)
    agent = st.session_state.notification_agent
    if (agent.state == "complete" or agent.state == "review_needed") and len(agent.notification_data) > 0:
        st.divider()
        # Header removed as per user request
        
        # Convert to list of dicts for data_editor
        import pandas as pd
        df = pd.DataFrame(agent.notification_data)
        
        # Use a dynamic key to force refresh when data changes externally
        if "table_key" not in st.session_state:
            st.session_state.table_key = 0
            
        # Display editable table
        edited_df = st.data_editor(
            df,
            width='stretch',
            num_rows="dynamic",  # Allow adding/removing rows
            column_config={
                "Milestone": st.column_config.TextColumn("Milestone", width="medium"),
                "Subject": st.column_config.TextColumn("Subject", width="large"),
                "Email": st.column_config.TextColumn("Email Body", width="large")
            },
            hide_index=True,
            key=f"notification_table_{st.session_state.table_key}"
        )
        
        # CRITICAL: Store the edited data in session state immediately
        # This ensures we always have access to the latest edits
        if edited_df is not None:
            st.session_state.latest_edited_data = edited_df.to_dict('records')
        
        # Buttons for table actions
        col1, col2, col3 = st.columns([2, 2, 6])
        
        with col1:
            if st.button("💾 Apply Changes", type="secondary"):
                # Update agent with edited data
                if edited_df is not None:
                    edited_data = edited_df.to_dict('records')
                    response = agent.update_from_table_edits(edited_data)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    # Increment key to reset the editor with new data
                    st.session_state.table_key += 1
                    rerun()
        
        with col2:
            # Show confirm button for both states
            if st.button("✅ Confirm & Continue", type="primary"):
                # CRITICAL: Capture edits from the table before confirming!
                # edited_df contains the current state of the table
                if edited_df is not None:
                    edited_data = edited_df.to_dict('records')
                    agent.update_from_table_edits(edited_data)
                
                if agent.state == "review_needed":
                    # Explicitly confirm modifications first
                    agent.confirm_modifications()
                    
                st.session_state.user_confirmed_data = True
                st.session_state.notification_complete = True
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Perfect! The notifications are validated. Click the button below to create the ticket."
                })
                rerun()

    # Show Redmine posting option only after explicit confirmation
    if st.session_state.notification_complete and st.session_state.user_confirmed_data:
        st.divider()
        st.markdown('<div class="success-box">✅ Notifications validated! You can now create the ticket.</div>', 
                   unsafe_allow_html=True)
        
        # Debug / Confirmation Preview
        with st.expander("👀 Preview Data to be Posted", expanded=True):
            st.write(st.session_state.notification_agent.notification_data)
        
        # Create Ticket Button
        if st.button("📤 Post to Redmine", type="primary", use_container_width=True):
            # CRITICAL: Use the latest edited data from session state
            if 'latest_edited_data' in st.session_state:
                agent.update_from_table_edits(st.session_state.latest_edited_data)
                st.toast("✅ Using latest edits!", icon="💾")
            
            ticket_data = st.session_state.ticket_data
            project_id = int(ticket_data["project_id"])
            
            with st.spinner("Creating ticket in Redmine..."):
                # Generate HTML table with wrapped text
                html_parts = []
                html_parts.append('<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">\n')
                html_parts.append('<tr style="background-color: #f0f0f0;">\n')
                html_parts.append('  <th style="text-align: left; width: 20%;">Milestone</th>\n')
                html_parts.append('  <th style="text-align: left; width: 30%;">Subject</th>\n')
                html_parts.append('  <th style="text-align: left; width: 50%;">Email</th>\n')
                html_parts.append('</tr>\n')
                
                for row in agent.notification_data:
                    m = row.get("Milestone", "").strip()
                    s = row.get("Subject", "").strip()
                    e = row.get("Email", "").strip()
                    
                    # Escape HTML special characters
                    import html
                    m = html.escape(m)
                    s = html.escape(s)
                    e = html.escape(e).replace('\n', '<br/>')
                    
                    html_parts.append('<tr>\n')
                    html_parts.append(f'  <td style="vertical-align: top; word-wrap: break-word;">{m}</td>\n')
                    html_parts.append(f'  <td style="vertical-align: top; word-wrap: break-word;">{s}</td>\n')
                    html_parts.append(f'  <td style="vertical-align: top; word-wrap: break-word;">{e}</td>\n')
                    html_parts.append('</tr>\n')
                
                html_parts.append('</table>')
                description_body = "".join(html_parts)
                
                # Generate TSV for attachment (keeps perfect tab-delimited data for scripts)
                import csv
                import io
                
                output = io.StringIO()
                headers = ["Milestone", "Subject", "Email"]
                writer = csv.DictWriter(output, fieldnames=headers, delimiter='\t')
                writer.writeheader()
                
                for row in agent.notification_data:
                    clean_row = {k: v.strip() for k, v in row.items()}
                    writer.writerow(clean_row)
                
                tsv_attachment_content = output.getvalue()
                
                # Append timestamp to subject
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                unique_subject = f"{ticket_data['subject']} - {timestamp}"
                
                # Prepare file attachment
                file_attachment = (
                    "notifications.tsv",
                    tsv_attachment_content.encode('utf-8'),
                    "text/tab-separated-values"
                )
                
                result = create_redmine_ticket(
                    str(project_id), 
                    unique_subject, 
                    description_body,
                    tracker_id=2,   # Feature
                    priority_id=2,  # Normal
                    file_attachment=file_attachment
                )
            
            if "Created Redmine Issue" in result:
                st.success(f"✅ {result}")
                st.balloons()
                # Clear state after success
                if st.button("🔄 Start New Ticket"):
                    st.session_state.page = "ticket_form"
                    st.session_state.notification_agent.reset()
                    st.session_state.messages = []
                    st.session_state.notification_complete = False
                    st.session_state.user_confirmed_data = False
                    st.session_state.show_editable_table = False
                    rerun()
            else:
                st.error(f"❌ {result}")
                st.error("Please check your Redmine configuration and permissions.")

    # Input area - ALWAYS AVAILABLE for corrections
    st.divider()
    with st.form(key="chat_form", clear_on_submit=True):
        st.markdown("**💬 Make corrections or paste new data:**")
        col1, col2 = st.columns([9, 1])
        
        with col1:
            user_input = st.text_area(
                "Your response:",
                key="user_input",
                placeholder="Type correction or paste new table...",
                label_visibility="collapsed",
                height=120
            )
        
        with col2:
            submit_button = st.form_submit_button("Send", type="primary")
        
        if submit_button and user_input:
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Reset confirmation if user is making changes
            st.session_state.user_confirmed_data = False
            st.session_state.notification_complete = False
            
            # Process the input
            response = st.session_state.notification_agent.process_user_response(user_input)
            st.session_state.messages.append({"role": "assistant", "content": response})
            rerun()

# Footer
st.divider()
st.caption("💡 Tip: Ensure your Excel table has columns: Milestone, Subject, Email")
