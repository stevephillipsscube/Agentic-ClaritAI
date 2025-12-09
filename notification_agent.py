# notification_agent.py
"""
Agentic Notification Validator
Validates Excel-formatted notification tables provided in ticket descriptions.
"""
import json
from typing import Dict, Any, List, Optional
from llm import chat


class NotificationAgent:
    """
    Agent that validates application notification tables.
    Ensures each row has Milestone, Subject, and Email.
    """
    
    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
        self.notification_data: List[Dict[str, str]] = []
        self.validation_errors: List[str] = []
        self.modifications_made: List[str] = []
        self.state = "validating"  # validating, correcting, review_needed, complete
        self.raw_input = ""
        
    def start_validation(self, description_text: str) -> str:
        """Start the validation process with the provided description text."""
        self.raw_input = description_text
        self.state = "validating"
        
        # Initial validation
        self._parse_and_validate(description_text)
        
        # Check for errors first
        if self.validation_errors:
            self.state = "correcting"
            return self.generate_error_report()
            
        # If no errors, check if we made modifications that need review
        if self.modifications_made:
            self.state = "review_needed"
            return self.generate_review_message()
            
        # If no errors and no modifications, we are complete
        if len(self.notification_data) > 0:
            self.state = "complete"
            return self.generate_success_message()
            
        return "No data found."

    def confirm_modifications(self):
        """User accepts the AI modifications."""
        self.state = "complete"
        return "✅ Modifications accepted. Validation complete."
    
    def process_user_response(self, user_input: str) -> str:
        """Process user input during correction phase."""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # If user provides new data (e.g. pasted corrected table), re-validate
        if "\t" in user_input or "Subject:" in user_input:
            # Assume it's a new table paste
            self._parse_and_validate(user_input)
        else:
            # Use LLM to apply corrections to existing data
            self._apply_correction_with_llm(user_input)
            
        if self.validation_errors:
            return self.generate_error_report()
            
        if self.modifications_made:
            self.state = "review_needed"
            return self.generate_review_message()
            
        if len(self.notification_data) > 0:
            self.state = "complete"
            return self.generate_success_message()
            
        return self.generate_error_report()
            
    def _parse_and_validate(self, text: str):
        """Parse text into rows and validate required fields."""
        self.notification_data = []
        self.validation_errors = []
        self.modifications_made = []
        
        lines = text.strip().split('\n')
        if not lines:
            self.validation_errors.append("No data found.")
            return

        # NEW APPROACH: Split by "Subject:" first, then parse each block
        import re
        
        # Find all "Subject:" occurrences and split the text
        subject_pattern = r'Subject:\s*'
        parts = re.split(subject_pattern, text, flags=re.IGNORECASE)
        
        # First part is header/junk before first Subject, skip it
        if len(parts) > 1:
            parts = parts[1:]  # Remove everything before first Subject:
        
        num_subjects = len(parts)
        
        if num_subjects == 0:
            self.validation_errors.append("No 'Subject:' lines found in the input. Please ensure your notifications include 'Subject:' lines.")
            return
            
        if num_subjects > 1:
            self.modifications_made.append(f"Split input into {num_subjects} separate notifications based on 'Subject:' lines.")
        
        # Now parse each block separately
        self.notification_data = []
        
        # Also split by Subject to find milestone names in between
        subject_splits = re.split(r'Subject:', text, flags=re.IGNORECASE)
        
        for i, block in enumerate(parts):
            # Each block starts with the subject text (after "Subject:")
            lines = block.strip().split('\n')
            if not lines:
                continue
                
            # Subject is the first line
            subject = lines[0].strip()
            original_subject = subject
            
            # Email body: everything after subject line, but STOP at common business rules keywords
            email_lines = []
            for line in lines[1:]:
                # Stop if we hit business rules indicators
                if any(keyword in line for keyword in ['Send when', 'Send this if', 'Sent when', 'Send after', '-Inspector will']):
                    break
                email_lines.append(line)
            
            email = '\n'.join(email_lines).strip()
            original_email = email
            
            # Clean up placeholders
            # Track changes for subject
            new_subject = re.sub(r'Application\s*_{2,}', '[Application]', subject)
            if new_subject != subject:
                self.modifications_made.append(f"Subject {i+1}: Replaced 'Application ____' with '[Application]'")
                subject = new_subject
                
            new_subject = re.sub(r'#{1,}\s*_{2,}', '#[Address]', subject)
            if new_subject != subject:
                self.modifications_made.append(f"Subject {i+1}: Replaced '#____' with '#[Address]'")
                subject = new_subject
                
            new_subject = re.sub(r'_{2,}', '[Address]', subject)
            if new_subject != subject:
                self.modifications_made.append(f"Subject {i+1}: Replaced '____' with '[Address]'")
                subject = new_subject
            
            # Track changes for email
            new_email = re.sub(r'Application\s*_{2,}', '[Application]', email)
            if new_email != email:
                self.modifications_made.append(f"Email {i+1}: Replaced 'Application ____' with '[Application]'")
                email = new_email
                
            new_email = re.sub(r'at\s*_{2,}|_{2,}address_{2,}|_{2,}', '[Address]', email)
            if new_email != email:
                self.modifications_made.append(f"Email {i+1}: Replaced address placeholders with '[Address]'")
                email = new_email
            
            # Extract milestone from the text BEFORE this Subject
            milestone = f"Notification {i+1}"  # Default
            
            if i < len(subject_splits) - 1:
                before_subject = subject_splits[i]
                # Get the last few lines before Subject
                before_lines = [l.strip() for l in before_subject.split('\n') if l.strip()]
                
                # Look backwards for the milestone name
                for line in reversed(before_lines[-5:]):  # Check last 5 lines
                    # Skip header rows and empty lines
                    if (line and 
                        'Notification Type' not in line and 
                        'Verbiage' not in line and 
                        'Business Rules' not in line and
                        'Subject:' not in line and
                        len(line) > 3 and
                        not line.startswith('Send') and
                        '\t' not in line):  # Skip tab-separated rows
                        milestone = line
                        break
            
            self.notification_data.append({
                "Milestone": milestone,
                "Subject": subject,
                "Email": email
            })
        
        # Validate we got the right number
        if len(self.notification_data) != num_subjects:
            self.validation_errors.append(f"Found {num_subjects} 'Subject:' line(s) but only created {len(self.notification_data)} notification(s).")
            return

    def _validate_rows(self):
        """Check for missing fields in parsed data."""
        self.validation_errors = []
        
        for i, row in enumerate(self.notification_data):
            missing = []
            if not row.get("Milestone"): missing.append("Milestone")
            if not row.get("Subject"): missing.append("Subject")
            if not row.get("Email"): missing.append("Email")
            
            if missing:
                self.validation_errors.append(f"Row {i+1} ({row.get('Milestone', 'Unknown')}): Missing {', '.join(missing)}")

    def _apply_correction_with_llm(self, user_input: str):
        """Use LLM to fix data based on user instruction."""
        system_prompt = f"""You are fixing notification data based on user feedback.

Current Data: {json.dumps(self.notification_data, indent=2)}

User's Corrections: {user_input}

Apply these corrections to the data. Common fixes:
- Replace "(Senders name)" or "(senders name)" with "[Senders Name]"
- Replace "1)" and "2)" with "[Comments]"
- Ensure [Application#] appears in subjects where needed
- Remove [Address] from subjects if user says so
- Fix any placeholder formatting issues
- Add Varibles where they arent implicitly listed.  
- Example Application __________ Should be Application [Application#]
- Revision at ______ Should be [Address]

Return the corrected data as JSON with key 'rows'.
"""
        
        try:
            result = chat(system_prompt, "Apply the corrections and return the updated JSON.")
            parsed = json.loads(result)
            if "rows" in parsed:
                self.notification_data = parsed["rows"]
                self._validate_rows()
            else:
                self.validation_errors.append("Could not apply corrections. Please paste the corrected table.")
        except Exception as e:
            self.validation_errors.append(f"Failed to apply correction: {str(e)}")

    def generate_review_message(self) -> str:
        """Generate a message listing the AI modifications."""
        msg = "⚠️ **Review AI Modifications**\n\n"
        msg += "I made the following changes to clean up your data:\n\n"
        for mod in self.modifications_made:
            msg += f"- {mod}\n"
            
        msg += "\n**Current Data Preview:**\n\n"
        msg += "| # | Milestone | Subject | Email Body |\n"
        msg += "|---|-----------|---------|------------|\n"
        
        for i, row in enumerate(self.notification_data, 1):
            milestone = row.get('Milestone', '').replace('|', '\\|')
            subject = row.get('Subject', '').replace('|', '\\|')
            email = row.get('Email', '').replace('|', '\\|')
            # Replace newlines with <br> for table display
            email_formatted = email.replace('\n', '<br>')
            
            msg += f"| {i} | {milestone} | {subject} | {email_formatted} |\n"
            
        msg += "\n**You can edit the data in the table below:**"
        return msg

    def generate_error_report(self) -> str:
        """Generate a friendly error report."""
        msg = "⚠️ **Validation Issues Found**\n\n"
        msg += "I found some missing information in your notifications table:\n\n"
        for err in self.validation_errors:
            msg += f"- {err}\n"
        msg += "\n**Please provide the missing details or paste a corrected table.**"
        return msg

    def generate_success_message(self) -> str:
        """Generate success message with preview."""
        # Double-check we actually have valid data
        if len(self.notification_data) == 0:
            return "❌ No notifications found. Please paste your notification table."
        
        msg = f"✅ **Parsing Complete!**\n\n"
        msg += f"Found **{len(self.notification_data)} notification(s)**.\n\n"
        
        # Display in table format with full content
        msg += "| # | Milestone | Subject | Email Body |\n"
        msg += "|---|-----------|---------|------------|\n"
        
        for i, row in enumerate(self.notification_data, 1):
            milestone = row.get('Milestone', '').replace('|', '\\|')
            subject = row.get('Subject', '').replace('|', '\\|')
            email = row.get('Email', '').replace('|', '\\|')
            # Replace newlines with <br> for table display
            email_formatted = email.replace('\n', '<br>')
            
            msg += f"| {i} | {milestone} | {subject} | {email_formatted} |\n"
            
        msg += "\n**Is this correct?** (Reply 'yes' to confirm, or describe what needs to be changed)"
        return msg
        
    def get_formatted_notification(self) -> str:
        """Return the final formatted data (JSON string for now)."""
        return json.dumps(self.notification_data, indent=2)
    
    def update_from_table_edits(self, edited_data: List[Dict[str, str]]) -> str:
        """Update notification data from user's table edits."""
        self.notification_data = edited_data
        self._validate_rows()
        
        if not self.validation_errors and len(self.notification_data) > 0:
            self.state = "complete"
            return "✅ Changes applied successfully!"
        else:
            self.state = "correcting"
            return self.generate_error_report()

    def reset(self):
        self.conversation_history = []
        self.notification_data = []
        self.validation_errors = []
        self.state = "validating"
