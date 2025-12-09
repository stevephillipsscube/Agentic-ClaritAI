# requirements_agent.py
import json
from typing import Dict, Any, List, Optional
from llm import chat
from tools.redmine_ops import list_redmine_projects


class RequirementsAgent:
    """
    Agentic chatbot that extracts requirements through conversation
    before creating a Redmine ticket.
    """
    
    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
        self.extracted_info: Dict[str, Any] = {
            "project_id": None,
            "project_name": None,
            "subject": None,
            "description": None,
            "priority": None,
            "assignee": None,
            "due_date": None,
            "additional_notes": None
        }
        self.projects: List[Dict[str, Any]] = []
        self.state = "greeting"  # greeting, gathering, confirming, complete
        self.load_projects()
        
    def load_projects(self):
        """Load available Redmine projects."""
        self.projects = list_redmine_projects()
        
    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find project by name (case-insensitive partial match)."""
        name_lower = name.lower()
        # Exact match first
        for p in self.projects:
            if p["name"].lower() == name_lower:
                return p
        # Partial match
        for p in self.projects:
            if name_lower in p["name"].lower():
                return p
        return None
    
    def start_conversation(self) -> str:
        """Generate initial greeting and first question."""
        self.state = "gathering"
        greeting = (
            "Hello! I'm here to help you create a work ticket. "
            "I'll ask you a few questions to make sure we capture all the important details.\n\n"
            "Let's start: **Which project is this ticket for?**"
        )
        if self.projects:
            project_list = ", ".join([f"'{p['name']}'" for p in self.projects[:5]])
            if len(self.projects) > 5:
                project_list += f", and {len(self.projects) - 5} more"
            greeting += f"\n\n_Available projects include: {project_list}_"
        
        self.conversation_history.append({"role": "assistant", "content": greeting})
        return greeting
    
    def process_user_response(self, user_input: str) -> str:
        """Process user input and generate next response."""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Use LLM to extract information from user input
        extraction_result = self._extract_information(user_input)
        
        # Update extracted info
        for key, value in extraction_result.items():
            if value and key in self.extracted_info:
                self.extracted_info[key] = value
        
        # Check if we're ready to confirm
        if self.is_ready_to_submit():
            self.state = "confirming"
            response = self.generate_ticket_summary()
        else:
            # Generate next question
            response = self.ask_next_question()
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    def _extract_information(self, user_input: str) -> Dict[str, Any]:
        """Use LLM to extract structured information from user input."""
        # Build context from conversation history
        context = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in self.conversation_history[-6:]  # Last 3 exchanges
        ])
        
        # Create list of available projects for validation
        project_names = [p["name"] for p in self.projects]
        
        system_prompt = f"""You are an information extraction assistant. Extract structured information from the user's message.

Available projects: {json.dumps(project_names)}

Current extracted information:
{json.dumps(self.extracted_info, indent=2)}

Extract any new or updated information from the user's latest message. Return ONLY a JSON object with these fields (use null for missing):
- project_name: exact project name if mentioned (must match available projects)
- subject: brief title/summary of the work
- description: detailed description of what needs to be done
- priority: one of [Low, Normal, High, Urgent] if mentioned
- assignee: person's name if mentioned
- due_date: any timeline or due date mentioned
- additional_notes: any other relevant details

Only include fields that are mentioned or can be inferred. If the user is providing new information that replaces old information, use the new value."""

        try:
            result = chat(system_prompt, f"Context:\n{context}\n\nLatest user message: {user_input}")
            extracted = json.loads(result)
            
            # Validate and map project name to ID
            if extracted.get("project_name"):
                project = self.get_project_by_name(extracted["project_name"])
                if project:
                    extracted["project_id"] = project["id"]
                    extracted["project_name"] = project["name"]  # Use exact name
                else:
                    extracted["project_name"] = None  # Invalid project
            
            return extracted
        except Exception as e:
            print(f"[AGENT] Extraction error: {e}")
            return {}
    
    def ask_next_question(self) -> str:
        """Generate the next question based on missing information."""
        missing = self.get_missing_required_fields()
        
        if not missing:
            return self.generate_ticket_summary()
        
        # Build context for LLM
        context = {
            "extracted_info": self.extracted_info,
            "missing_fields": missing,
            "conversation_history": self.conversation_history[-4:]  # Last 2 exchanges
        }
        
        system_prompt = """You are a helpful requirements gathering assistant. Your job is to ask the next most important question to gather missing information for a work ticket.

Current situation:
- Extracted information: {extracted_info}
- Missing required fields: {missing_fields}
- Recent conversation: {conversation_history}

Generate a natural, conversational question to gather the next piece of missing information. 
- Be friendly and professional
- Ask about ONE thing at a time
- If project is missing or invalid, ask about it first
- If subject is missing, ask for a brief title/summary
- If description is missing, ask for details about what needs to be done
- For optional fields (priority, assignee, due_date), ask if they seem relevant

Return ONLY the question text, no JSON.""".format(
            extracted_info=json.dumps(self.extracted_info, indent=2),
            missing_fields=", ".join(missing),
            conversation_history=json.dumps([
                {"role": msg["role"], "content": msg["content"][:100]} 
                for msg in context["conversation_history"]
            ])
        )
        
        try:
            question = chat(system_prompt, "Generate the next question:")
            # Clean up any JSON artifacts
            question = question.strip().strip('"{}')
            return question
        except Exception as e:
            print(f"[AGENT] Question generation error: {e}")
            # Fallback to simple question
            if "project_id" in missing:
                return "Which project should this ticket be created for?"
            elif "subject" in missing:
                return "What should be the title or subject of this ticket?"
            elif "description" in missing:
                return "Can you provide more details about what needs to be done?"
            else:
                return "Is there anything else you'd like to add?"
    
    def get_missing_required_fields(self) -> List[str]:
        """Return list of required fields that are still missing."""
        required = ["project_id", "subject", "description"]
        missing = []
        
        for field in required:
            value = self.extracted_info.get(field)
            if not value or (isinstance(value, str) and len(value.strip()) < 3):
                missing.append(field)
        
        return missing
    
    def is_ready_to_submit(self) -> bool:
        """Check if all required information has been collected."""
        return len(self.get_missing_required_fields()) == 0
    
    def generate_ticket_summary(self) -> str:
        """Generate a summary of the ticket for user confirmation."""
        info = self.extracted_info
        
        summary = "Great! I have all the information I need. Here's a summary of the ticket:\n\n"
        summary += f"**Project:** {info['project_name']}\n"
        summary += f"**Subject:** {info['subject']}\n"
        summary += f"**Description:** {info['description']}\n"
        
        if info.get('priority'):
            summary += f"**Priority:** {info['priority']}\n"
        if info.get('assignee'):
            summary += f"**Assignee:** {info['assignee']}\n"
        if info.get('due_date'):
            summary += f"**Due Date:** {info['due_date']}\n"
        if info.get('additional_notes'):
            summary += f"**Additional Notes:** {info['additional_notes']}\n"
        
        summary += "\n**Does this look correct?** (You can reply 'yes' to create the ticket, or provide any corrections)"
        
        return summary
    
    def get_ticket_data(self) -> Dict[str, Any]:
        """Get the extracted information formatted for ticket creation."""
        return {
            "project_id": str(self.extracted_info["project_id"]),
            "subject": self.extracted_info["subject"],
            "description": self._build_full_description()
        }
    
    def _build_full_description(self) -> str:
        """Build complete description including all gathered information."""
        parts = [self.extracted_info["description"]]
        
        if self.extracted_info.get("priority"):
            parts.append(f"\n**Priority:** {self.extracted_info['priority']}")
        
        if self.extracted_info.get("assignee"):
            parts.append(f"**Requested Assignee:** {self.extracted_info['assignee']}")
        
        if self.extracted_info.get("due_date"):
            parts.append(f"**Timeline:** {self.extracted_info['due_date']}")
        
        if self.extracted_info.get("additional_notes"):
            parts.append(f"\n**Additional Notes:**\n{self.extracted_info['additional_notes']}")
        
        return "\n".join(parts)
    
    def reset(self):
        """Reset the agent for a new conversation."""
        self.conversation_history = []
        self.extracted_info = {
            "project_id": None,
            "project_name": None,
            "subject": None,
            "description": None,
            "priority": None,
            "assignee": None,
            "due_date": None,
            "additional_notes": None
        }
        self.state = "greeting"
        self.load_projects()  # Refresh project list
