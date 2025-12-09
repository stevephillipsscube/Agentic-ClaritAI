import os
import requests
import json
import html
from typing import Optional, Dict, Any, List

class RedmineClient:
    def __init__(self):
        self.url = os.getenv("RM_URL", "").rstrip("/")
        self.username = os.getenv("RM_USERNAME")
        self.password = os.getenv("RM_PASSWORD")
        self.token = os.getenv("RM_SECURITY_TOKEN")
        
        if not self.url:
            print("[Redmine] WARN: RM_URL not set in .env")

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Redmine-API-Key"] = self.token
        return headers

    def _get_auth(self) -> Optional[tuple]:
        if not self.token and self.username and self.password:
            return (self.username, self.password)
        return None

    def upload_file(self, file_content: bytes, filename: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """Uploads a file to Redmine and returns the token."""
        if not self.url:
            return None
            
        endpoint = f"{self.url}/uploads.json"
        headers = {"Content-Type": "application/octet-stream"}
        if self.token:
            headers["X-Redmine-API-Key"] = self.token
            
        try:
            resp = requests.post(
                endpoint, 
                data=file_content, 
                headers=headers,
                params={"filename": filename}
            )
            if resp.status_code == 201:
                return resp.json()["upload"]["token"]
            return None
        except Exception as e:
            print(f"Upload failed: {e}")
            return None

    def create_issue(self, project_id: str, subject: str, description: str = "", tracker_id: int = 2, priority_id: int = 2, uploads: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Creates a new issue in Redmine using XML (workaround for JSON issues)."""
        if not self.url:
            return {"error": "Redmine URL not configured"}

        # Use XML payload as JSON seems to fail on this server
        # Escape subject, but use CDATA for description to preserve newlines and formatting
        safe_subject = html.escape(subject)
        
        # CDATA allows us to send newlines and special chars like <br> and | without them being parsed as XML
        # We only need to escape ']]>' if it appears in the text (unlikely but good practice)
        safe_description = description.replace("]]>", "]]]]><![CDATA[>")
        
        uploads_xml = ""
        if uploads:
            uploads_xml = '<uploads type="array">'
            for upload in uploads:
                uploads_xml += f"""
                <upload>
                    <token>{upload['token']}</token>
                    <filename>{upload['filename']}</filename>
                    <content_type>{upload['content_type']}</content_type>
                </upload>"""
            uploads_xml += '</uploads>'
        
        xml_payload = f"""<?xml version="1.0"?>
<issue>
    <project_id>{project_id}</project_id>
    <subject>{safe_subject}</subject>
    <description><![CDATA[{safe_description}]]></description>
    <tracker_id>{tracker_id}</tracker_id>
    <priority_id>{priority_id}</priority_id>
    {uploads_xml}
</issue>"""

        headers = {
            "Content-Type": "application/xml",
            "X-Redmine-API-Key": self.token
        }
        
        endpoint = f"{self.url}/issues.xml"
        
        try:
            resp = requests.post(
                endpoint, 
                data=xml_payload, 
                headers=headers, 
                timeout=10
            )
            
            # Happy path: 201 Created
            if resp.status_code == 201:
                return resp.json()
                
            # Workaround: Server returns 404 but might have created the ticket
            if resp.status_code == 404:
                # Search for the ticket we just tried to create
                import time
                time.sleep(1) # Give it a moment
                
                check_resp = requests.get(
                    f"{self.url}/issues.json",
                    params={"project_id": project_id, "subject": subject, "limit": 1},
                    headers={"Content-Type": "application/json", "X-Redmine-API-Key": self.token}
                )
                
                if check_resp.status_code == 200:
                    issues = check_resp.json().get("issues", [])
                    if issues:
                        # Check if the ticket is recent (created in the last minute)
                        # Redmine returns UTC timestamps like '2025-12-06T17:20:54Z'
                        from datetime import datetime, timedelta, timezone
                        
                        found_issue = issues[0]
                        created_on_str = found_issue.get("created_on")
                        
                        if created_on_str:
                            # Parse timestamp (handle Z for UTC)
                            created_on = datetime.fromisoformat(created_on_str.replace("Z", "+00:00"))
                            now = datetime.now(timezone.utc)
                            
                            # If created within the last 60 seconds, it's our ticket
                            if (now - created_on) < timedelta(seconds=60):
                                return {"issue": found_issue}
                            else:
                                # Found an old ticket, not the one we just tried to create
                                return {"error": "Creation failed (404), and only found old tickets with same subject."}
                        
                        # Fallback if no timestamp (unlikely)
                        return {"issue": found_issue}
            
            # If we get here, it really failed
            resp.raise_for_status()
            return resp.json()
            
        except Exception as e:
            # Return detailed error info
            error_details = {
                "error": str(e),
                "status_code": resp.status_code if 'resp' in locals() else None,
                "response_text": resp.text if 'resp' in locals() else "",
            }
            return error_details

    def list_issues(self, limit: int = 5) -> Dict[str, Any]:
        """Lists recent issues."""
        if not self.url:
            return {"error": "Redmine URL not configured"}

        endpoint = f"{self.url}/issues.json?limit={limit}"
        try:
            resp = requests.get(
                endpoint, 
                headers=self._get_headers(), 
                auth=self._get_auth()
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_issue(self, issue_id: int) -> Dict[str, Any]:
        """Gets details of a specific issue."""
        if not self.url:
            return {"error": "Redmine URL not configured"}

        endpoint = f"{self.url}/issues/{issue_id}.json"
        try:
            resp = requests.get(
                endpoint, 
                headers=self._get_headers(), 
                auth=self._get_auth()
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def get_projects(self) -> Dict[str, Any]:
        """Lists all projects with pagination support."""
        if not self.url:
            return {"error": "Redmine URL not configured"}

        all_projects = []
        limit = 100  # Maximum allowed by Redmine API
        offset = 0
        
        try:
            while True:
                endpoint = f"{self.url}/projects.json?limit={limit}&offset={offset}"
                resp = requests.get(
                    endpoint, 
                    headers=self._get_headers(), 
                    auth=self._get_auth()
                )
                resp.raise_for_status()
                data = resp.json()
                
                projects = data.get("projects", [])
                if not projects:
                    break
                    
                all_projects.extend(projects)
                
                # Check if we've retrieved all projects
                total_count = data.get("total_count", 0)
                if len(all_projects) >= total_count:
                    break
                    
                offset += limit
            
            return {"projects": all_projects, "total_count": len(all_projects)}
        except Exception as e:
            return {"error": str(e)}

def create_redmine_ticket(project_id: str, subject: str, description: str = "", tracker_id: int = 2, priority_id: int = 2, file_attachment: Optional[tuple] = None) -> str:
    client = RedmineClient()
    
    uploads = []
    if file_attachment:
        filename, content, content_type = file_attachment
        token = client.upload_file(content, filename, content_type)
        if token:
            uploads.append({
                "token": token,
                "filename": filename,
                "content_type": content_type
            })
        else:
            return "Failed to upload attachment."
            
    res = client.create_issue(project_id, subject, description, tracker_id, priority_id, uploads=uploads)
    if "issue" in res:
        return f"Created Redmine Issue #{res['issue']['id']}: {res['issue']['subject']}"
    return f"Failed to create issue: {res}"

def list_redmine_tickets(limit: int = 5) -> str:
    client = RedmineClient()
    res = client.list_issues(limit)
    if "issues" in res:
        lines = [f"#{i['id']} - {i['subject']} ({i['status']['name']})" for i in res['issues']]
        return "\n".join(lines)
    return f"Failed to list issues: {res}"

def list_redmine_projects() -> List[Dict[str, Any]]:
    client = RedmineClient()
    res = client.get_projects()
    if "projects" in res:
        return res["projects"]
    return []
