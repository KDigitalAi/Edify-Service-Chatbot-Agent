from typing import Dict, Any, List, Optional
from app.db.crm_repo import CRMRepo
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Registry of CRM tools available for agentic operations.
    Maps tool names to CRMRepo methods with OpenAI function schemas.
    """
    
    def __init__(self):
        self.crm_repo = CRMRepo()
        self.tools = self._initialize_tools()
    
    def _initialize_tools(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all CRM tools with OpenAI function schemas."""
        return {
            "create_lead": {
                "function": self.crm_repo.create_lead,
                "schema": {
                    "name": "create_lead",
                    "description": "Create a new lead in the CRM system. Use this when user wants to add a new lead, prospect, or potential customer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Full name of the lead"
                            },
                            "email": {
                                "type": "string",
                                "description": "Email address of the lead"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number of the lead (required)"
                            },
                            "lead_status": {
                                "type": "string",
                                "description": "Status of the lead (e.g., 'Not Contacted', 'Contacted', 'Qualified')"
                            },
                            "lead_stage": {
                                "type": "string",
                                "description": "Stage of the lead (e.g., 'lead', 'opportunity')"
                            },
                            "opportunity_status": {
                                "type": "string",
                                "description": "Opportunity status (e.g., 'Visiting', 'Enrolled', 'Dropped')"
                            },
                            "lead_source": {
                                "type": "string",
                                "description": "Source of the lead (e.g., 'Website', 'Referral', 'Email Campaign')"
                            },
                            "lead_owner": {
                                "type": "string",
                                "description": "Owner of the lead (optional)"
                            },
                            "fee_quoted": {
                                "type": "integer",
                                "description": "Fee quoted to the lead (optional)"
                            },
                            "next_follow_up": {
                                "type": "string",
                                "description": "Next follow-up date (ISO format, optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the lead (optional)"
                            }
                        },
                        "required": ["name", "phone"]
                    }
                }
            },
            "update_lead": {
                "function": self.crm_repo.update_lead,
                "schema": {
                    "name": "update_lead",
                    "description": "Update an existing lead's information. Use this when user wants to modify lead details like status, contact info, or notes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lead_id": {
                                "type": "string",
                                "description": "ID of the lead to update"
                            },
                            "name": {
                                "type": "string",
                                "description": "Updated name (optional)"
                            },
                            "email": {
                                "type": "string",
                                "description": "Updated email (optional)"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Updated phone (optional)"
                            },
                            "lead_status": {
                                "type": "string",
                                "description": "Updated status (optional)"
                            },
                            "lead_stage": {
                                "type": "string",
                                "description": "Updated stage (optional)"
                            },
                            "opportunity_status": {
                                "type": "string",
                                "description": "Updated opportunity status (optional)"
                            },
                            "fee_quoted": {
                                "type": "integer",
                                "description": "Updated fee quoted (optional)"
                            },
                            "next_follow_up": {
                                "type": "string",
                                "description": "Updated next follow-up date (ISO format, optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Updated description (optional)"
                            }
                        },
                        "required": ["lead_id"]
                    }
                }
            },
            "delete_lead": {
                "function": self.crm_repo.delete_lead,
                "schema": {
                    "name": "delete_lead",
                    "description": "Delete a lead from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lead_id": {
                                "type": "string",
                                "description": "ID of the lead to delete"
                            }
                        },
                        "required": ["lead_id"]
                    }
                }
            },
            "create_campaign": {
                "function": self.crm_repo.create_campaign,
                "schema": {
                    "name": "create_campaign",
                    "description": "Create a new marketing campaign in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Campaign name"
                            },
                            "status": {
                                "type": "string",
                                "description": "Campaign status",
                                "enum": ["Planning", "Active", "Paused", "Completed", "Cancelled"]
                            },
                            "type": {
                                "type": "string",
                                "description": "Campaign type (e.g., 'Email', 'Social Media', 'Webinar')"
                            },
                            "campaign_owner": {
                                "type": "string",
                                "description": "Owner of the campaign"
                            },
                            "campaign_date": {
                                "type": "string",
                                "description": "Campaign start date (optional, accepts formats like '7/2/2026', '2026-07-02', or ISO format)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Campaign end date (optional, accepts formats like '7/2/2026', '2026-07-02', or ISO format)"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Campaign phone number (optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Campaign description (optional)"
                            }
                        },
                        "required": ["name", "status", "type"]
                    }
                }
            },
            "update_campaign": {
                "function": self.crm_repo.update_campaign,
                "schema": {
                    "name": "update_campaign",
                    "description": "Update an existing campaign's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campaign_id": {
                                "type": "string",
                                "description": "ID of the campaign to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)",
                                "enum": ["Planning", "Active", "Paused", "Completed", "Cancelled"]
                            },
                            "name": {
                                "type": "string",
                                "description": "Updated name (optional)"
                            },
                            "campaign_date": {
                                "type": "string",
                                "description": "Campaign start date (optional, accepts formats like '7/2/2026', '2026-07-02', or ISO format)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Campaign end date (optional, accepts formats like '7/2/2026', '2026-07-02', or ISO format)"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Updated phone number (optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Updated description (optional)"
                            }
                        },
                        "required": ["campaign_id"]
                    }
                }
            },
            "create_task": {
                "function": self.crm_repo.create_task,
                "schema": {
                    "name": "create_task",
                    "description": "Create a new task in the CRM system. Use this when user wants to create a todo, reminder, or follow-up task.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Task subject or title"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Task priority",
                                "enum": ["Low", "Medium", "High", "Urgent"]
                            },
                            "status": {
                                "type": "string",
                                "description": "Task status",
                                "enum": ["Not Started", "In Progress", "Completed", "Cancelled"]
                            },
                            "task_type": {
                                "type": "string",
                                "description": "Type of task (e.g., 'Call', 'Email', 'Meeting', 'Follow-up')"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date for the task (ISO format, optional)"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Associated lead ID (optional)"
                            },
                            "batch_id": {
                                "type": "integer",
                                "description": "Associated batch ID (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Associated trainer ID (optional)"
                            },
                            "campaign_id": {
                                "type": "integer",
                                "description": "Associated campaign ID (optional)"
                            },
                            "learner_id": {
                                "type": "integer",
                                "description": "Associated learner ID (optional)"
                            }
                        },
                        "required": ["subject", "priority", "status"]
                    }
                }
            },
            "update_task": {
                "function": self.crm_repo.update_task,
                "schema": {
                    "name": "update_task",
                    "description": "Update an existing task's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)",
                                "enum": ["Not Started", "In Progress", "Completed", "Cancelled"]
                            },
                            "priority": {
                                "type": "string",
                                "description": "Updated priority (optional)",
                                "enum": ["Low", "Medium", "High", "Urgent"]
                            },
                            "subject": {
                                "type": "string",
                                "description": "Updated subject (optional)"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Updated due date (ISO format, optional)"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Updated associated lead ID (optional)"
                            },
                            "batch_id": {
                                "type": "integer",
                                "description": "Updated associated batch ID (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Updated associated trainer ID (optional)"
                            },
                            "campaign_id": {
                                "type": "integer",
                                "description": "Updated associated campaign ID (optional)"
                            },
                            "learner_id": {
                                "type": "integer",
                                "description": "Updated associated learner ID (optional)"
                            }
                        },
                        "required": ["task_id"]
                    }
                }
            },
            "create_trainer": {
                "function": self.crm_repo.create_trainer,
                "schema": {
                    "name": "create_trainer",
                    "description": "Create a new trainer record in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "trainer_name": {
                                "type": "string",
                                "description": "Full name of the trainer"
                            },
                            "email": {
                                "type": "string",
                                "description": "Email address"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number (optional)"
                            },
                            "trainer_status": {
                                "type": "string",
                                "description": "Status of the trainer",
                                "enum": ["Active", "Inactive", "On Leave"]
                            },
                            "tech_stack": {
                                "type": "string",
                                "description": "Technical skills or technologies (optional)"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location (optional)"
                            },
                            "joining_date": {
                                "type": "string",
                                "description": "Joining date (ISO format, optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description (optional)"
                            }
                        },
                        "required": ["trainer_name", "email", "trainer_status"]
                    }
                }
            },
            "update_trainer": {
                "function": self.crm_repo.update_trainer,
                "schema": {
                    "name": "update_trainer",
                    "description": "Update an existing trainer's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "trainer_id": {
                                "type": "string",
                                "description": "ID of the trainer to update"
                            },
                            "trainer_status": {
                                "type": "string",
                                "description": "Updated status (optional)",
                                "enum": ["Active", "Inactive", "On Leave"]
                            },
                            "email": {
                                "type": "string",
                                "description": "Updated email (optional)"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Updated phone (optional)"
                            },
                            "tech_stack": {
                                "type": "string",
                                "description": "Updated tech stack (optional)"
                            },
                            "joining_date": {
                                "type": "string",
                                "description": "Updated joining date (ISO format, optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Updated description (optional)"
                            }
                        },
                        "required": ["trainer_id"]
                    }
                }
            },
            "create_learner": {
                "function": self.crm_repo.create_learner,
                "schema": {
                    "name": "create_learner",
                    "description": "Create a new learner record in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Full name of the learner"
                            },
                            "email": {
                                "type": "string",
                                "description": "Email address"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number (optional)"
                            },
                            "status": {
                                "type": "string",
                                "description": "Learner status",
                                "enum": ["Active", "Inactive", "Completed", "Dropped"]
                            },
                            "course": {
                                "type": "string",
                                "description": "Course name or ID (optional)"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location (optional)"
                            },
                            "id_proof": {
                                "type": "string",
                                "description": "ID proof document (optional)"
                            },
                            "date_of_birth": {
                                "type": "string",
                                "description": "Date of birth (ISO format, optional)"
                            },
                            "registered_date": {
                                "type": "string",
                                "description": "Registration date (ISO format, optional)"
                            },
                            "batch_id": {
                                "type": "string",
                                "description": "Batch ID (optional)"
                            },
                            "source": {
                                "type": "string",
                                "description": "Source of learner (optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description (optional)"
                            },
                            "total_fees": {
                                "type": "string",
                                "description": "Total fees (optional)"
                            },
                            "mode_of_installment_payment": {
                                "type": "string",
                                "description": "Payment mode (optional)"
                            },
                            "fees_paid": {
                                "type": "string",
                                "description": "Fees paid (optional)"
                            },
                            "due_amount": {
                                "type": "string",
                                "description": "Due amount (optional)"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date (ISO format, optional)"
                            },
                            "course": {
                                "type": "string",
                                "description": "Course name or ID (optional)"
                            },
                            "country_code": {
                                "type": "string",
                                "description": "Country code (optional)"
                            },
                            "payment_id": {
                                "type": "string",
                                "description": "Payment ID (optional)"
                            }
                        },
                        "required": ["name", "phone"]
                    }
                }
            },
            "update_learner": {
                "function": self.crm_repo.update_learner,
                "schema": {
                    "name": "update_learner",
                    "description": "Update an existing learner's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "learner_id": {
                                "type": "string",
                                "description": "ID of the learner to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)",
                                "enum": ["Active", "Inactive", "Completed", "Dropped"]
                            },
                            "email": {
                                "type": "string",
                                "description": "Updated email (optional)"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Updated phone (optional)"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)"
                            },
                            "location": {
                                "type": "string",
                                "description": "Updated location (optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Updated description (optional)"
                            },
                            "course": {
                                "type": "string",
                                "description": "Updated course (optional)"
                            }
                        },
                        "required": ["learner_id"]
                    }
                }
            },
            "create_course": {
                "function": self.crm_repo.create_course,
                "schema": {
                    "name": "create_course",
                    "description": "Create a new course in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Course title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Course description (optional)"
                            },
                            "trainer": {
                                "type": "string",
                                "description": "Trainer name or ID (optional)"
                            },
                            "duration": {
                                "type": "string",
                                "description": "Course duration (e.g., '40 hours', '8 weeks') (optional)"
                            },
                            "picture": {
                                "type": "string",
                                "description": "Course picture URL (optional)"
                            },
                            "archived": {
                                "type": "boolean",
                                "description": "Whether course is archived (optional)"
                            },
                            "liveLink": {
                                "type": "string",
                                "description": "Live link URL (optional)"
                            },
                            "contentLink": {
                                "type": "string",
                                "description": "Content link URL (optional)"
                            },
                            "trainer": {
                                "type": "string",
                                "description": "Trainer name or ID (optional)"
                            }
                        },
                        "required": ["title", "description", "picture"]
                    }
                }
            },
            "update_course": {
                "function": self.crm_repo.update_course,
                "schema": {
                    "name": "update_course",
                    "description": "Update an existing course's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "course_id": {
                                "type": "string",
                                "description": "ID of the course to update"
                            },
                            "title": {
                                "type": "string",
                                "description": "Updated title (optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Updated description (optional)"
                            },
                            "duration": {
                                "type": "string",
                                "description": "Updated duration (optional)"
                            },
                            "picture": {
                                "type": "string",
                                "description": "Updated picture URL (optional)"
                            },
                            "archived": {
                                "type": "boolean",
                                "description": "Updated archived status (optional)"
                            },
                            "liveLink": {
                                "type": "string",
                                "description": "Updated live link URL (optional)"
                            },
                            "contentLink": {
                                "type": "string",
                                "description": "Updated content link URL (optional)"
                            }
                        },
                        "required": ["course_id"]
                    }
                }
            },
            "create_activity": {
                "function": self.crm_repo.create_activity,
                "schema": {
                    "name": "create_activity",
                    "description": "Create a new activity log in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "activity_name": {
                                "type": "string",
                                "description": "Name or title of the activity"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Associated lead ID (optional)"
                            },
                            "batch_id": {
                                "type": "integer",
                                "description": "Associated batch ID (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Associated trainer ID (optional)"
                            },
                            "campaign_id": {
                                "type": "integer",
                                "description": "Associated campaign ID (optional)"
                            },
                            "learner_id": {
                                "type": "integer",
                                "description": "Associated learner ID (optional)"
                            }
                        },
                        "required": ["activity_name"]
                    }
                }
            },
            "create_note": {
                "function": self.crm_repo.create_note,
                "schema": {
                    "name": "create_note",
                    "description": "Create a new note in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Note content"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Associated lead ID (optional)"
                            },
                            "batch_id": {
                                "type": "integer",
                                "description": "Associated batch ID (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Associated trainer ID (optional)"
                            },
                            "campaign_id": {
                                "type": "integer",
                                "description": "Associated campaign ID (optional)"
                            },
                            "learner_id": {
                                "type": "integer",
                                "description": "Associated learner ID (optional)"
                            }
                        },
                        "required": ["content"]
                    }
                }
            },
            "create_batch": {
                "function": self.crm_repo.create_batch,
                "schema": {
                    "name": "create_batch",
                    "description": "Create a new training batch in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "batch_name": {
                                "type": "string",
                                "description": "Batch name"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location (optional)"
                            },
                            "slot": {
                                "type": "string",
                                "description": "Time slot (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Trainer ID (optional)"
                            },
                            "batch_status": {
                                "type": "string",
                                "description": "Batch status (e.g., 'Upcoming', 'Active', 'Completed')"
                            },
                            "stack": {
                                "type": "string",
                                "description": "Technology stack (optional)"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date (ISO format, optional)"
                            },
                            "tentative_end_date": {
                                "type": "string",
                                "description": "Tentative end date (ISO format, optional)"
                            },
                            "course_id": {
                                "type": "integer",
                                "description": "Course ID (optional)"
                            }
                        },
                        "required": ["batch_name"]
                    }
                }
            },
            "update_batch": {
                "function": self.crm_repo.update_batch,
                "schema": {
                    "name": "update_batch",
                    "description": "Update an existing batch's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "batch_id": {
                                "type": "string",
                                "description": "ID of the batch to update"
                            },
                            "batch_name": {
                                "type": "string",
                                "description": "Updated batch name (optional)"
                            },
                            "batch_status": {
                                "type": "string",
                                "description": "Updated batch status (optional)"
                            },
                            "location": {
                                "type": "string",
                                "description": "Updated location (optional)"
                            },
                            "stack": {
                                "type": "string",
                                "description": "Updated stack (optional)"
                            },
                            "course_id": {
                                "type": "integer",
                                "description": "Updated course ID (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Updated trainer ID (optional)"
                            }
                        },
                        "required": ["batch_id"]
                    }
                }
            },
            "create_email": {
                "function": self.crm_repo.create_email,
                "schema": {
                    "name": "create_email",
                    "description": "Create a new email record in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Email subject"
                            },
                            "to": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Recipient email addresses (array)"
                            },
                            "from": {
                                "type": "string",
                                "description": "Sender email address"
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body content"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Associated lead ID (optional)"
                            }
                        },
                        "required": ["to", "from", "subject"]
                    }
                }
            },
            "update_email": {
                "function": self.crm_repo.update_email,
                "schema": {
                    "name": "update_email",
                    "description": "Update an existing email record's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_id": {
                                "type": "string",
                                "description": "ID of the email to update"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Updated subject (optional)"
                            },
                            "to": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Updated recipient email addresses (optional)"
                            },
                            "from": {
                                "type": "string",
                                "description": "Updated sender email address (optional)"
                            },
                            "body": {
                                "type": "string",
                                "description": "Updated email body (optional)"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Updated associated lead ID (optional)"
                            }
                        },
                        "required": ["email_id"]
                    }
                }
            },
            "create_call": {
                "function": self.crm_repo.create_call,
                "schema": {
                    "name": "create_call",
                    "description": "Create a new call record in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "caller_id": {
                                "type": "string",
                                "description": "Caller ID"
                            },
                            "to": {
                                "type": "string",
                                "description": "Recipient phone number"
                            },
                            "status": {
                                "type": "string",
                                "description": "Call status"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Agent ID"
                            },
                            "time": {
                                "type": "integer",
                                "description": "Call time in seconds"
                            },
                            "direction": {
                                "type": "string",
                                "description": "Call direction (e.g., 'inbound', 'outbound')"
                            },
                            "answered_seconds": {
                                "type": "integer",
                                "description": "Answered duration in seconds"
                            },
                            "filename": {
                                "type": "string",
                                "description": "Call recording filename"
                            }
                        },
                        "required": ["caller_id", "to", "status", "agent_id", "time", "direction", "answered_seconds", "filename"]
                    }
                }
            },
            "update_call": {
                "function": self.crm_repo.update_call,
                "schema": {
                    "name": "update_call",
                    "description": "Update an existing call record's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "call_id": {
                                "type": "string",
                                "description": "ID of the call to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)"
                            },
                            "time": {
                                "type": "integer",
                                "description": "Updated call time in seconds (optional)"
                            },
                            "answered_seconds": {
                                "type": "integer",
                                "description": "Updated answered duration in seconds (optional)"
                            }
                        },
                        "required": ["call_id"]
                    }
                }
            },
            "create_meeting": {
                "function": self.crm_repo.create_meeting,
                "schema": {
                    "name": "create_meeting",
                    "description": "Create a new meeting record in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meeting_name": {
                                "type": "string",
                                "description": "Meeting name"
                            },
                            "location": {
                                "type": "string",
                                "description": "Meeting location"
                            },
                            "zoom_meeting_id": {
                                "type": "string",
                                "description": "Zoom meeting ID"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Meeting start time (ISO format)"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Meeting end time (ISO format)"
                            },
                            "host_id": {
                                "type": "string",
                                "description": "Host ID (optional)"
                            },
                            "participants": {
                                "type": "object",
                                "description": "Participants JSON (optional)"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Associated lead ID (optional)"
                            },
                            "batch_id": {
                                "type": "integer",
                                "description": "Associated batch ID (optional)"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User ID"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Associated trainer ID (optional)"
                            },
                            "campaign_id": {
                                "type": "integer",
                                "description": "Associated campaign ID (optional)"
                            },
                            "learner_id": {
                                "type": "integer",
                                "description": "Associated learner ID (optional)"
                            },
                            "main_task_id": {
                                "type": "integer",
                                "description": "Main task ID (optional)"
                            }
                        },
                        "required": ["meeting_name", "location", "zoom_meeting_id", "start_time", "end_time", "user_id"]
                    }
                }
            },
            "update_meeting": {
                "function": self.crm_repo.update_meeting,
                "schema": {
                    "name": "update_meeting",
                    "description": "Update an existing meeting record's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "ID of the meeting to update"
                            },
                            "meeting_name": {
                                "type": "string",
                                "description": "Updated meeting name (optional)"
                            },
                            "location": {
                                "type": "string",
                                "description": "Updated location (optional)"
                            },
                            "zoom_meeting_id": {
                                "type": "string",
                                "description": "Updated zoom meeting ID (optional)"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Updated start time (ISO format, optional)"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "Updated end time (ISO format, optional)"
                            },
                            "host_id": {
                                "type": "string",
                                "description": "Updated host ID (optional)"
                            },
                            "participants": {
                                "type": "object",
                                "description": "Updated participants JSON (optional)"
                            }
                        },
                        "required": ["meeting_id"]
                    }
                }
            },
            "create_message": {
                "function": self.crm_repo.create_message,
                "schema": {
                    "name": "create_message",
                    "description": "Create a new message record in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Message subject (optional)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Message content"
                            },
                            "status": {
                                "type": "string",
                                "description": "Message status (e.g., 'Draft', 'Sent', 'Delivered')"
                            },
                            "message_type": {
                                "type": "string",
                                "description": "Type of message (e.g., 'SMS', 'Chat', 'WhatsApp')"
                            },
                            "recipient": {
                                "type": "string",
                                "description": "Recipient identifier (optional)"
                            }
                        },
                        "required": ["content", "status"]
                    }
                }
            },
            "update_message": {
                "function": self.crm_repo.update_message,
                "schema": {
                    "name": "update_message",
                    "description": "Update an existing message record's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "ID of the message to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Updated content (optional)"
                            }
                        },
                        "required": ["message_id"]
                    }
                }
            },
            "delete_campaign": {
                "function": self.crm_repo.delete_campaign,
                "schema": {
                    "name": "delete_campaign",
                    "description": "Delete a campaign from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campaign_id": {
                                "type": "string",
                                "description": "ID of the campaign to delete"
                            }
                        },
                        "required": ["campaign_id"]
                    }
                }
            },
            "delete_task": {
                "function": self.crm_repo.delete_task,
                "schema": {
                    "name": "delete_task",
                    "description": "Delete a task from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task to delete"
                            }
                        },
                        "required": ["task_id"]
                    }
                }
            },
            "delete_trainer": {
                "function": self.crm_repo.delete_trainer,
                "schema": {
                    "name": "delete_trainer",
                    "description": "Delete a trainer from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "trainer_id": {
                                "type": "string",
                                "description": "ID of the trainer to delete"
                            }
                        },
                        "required": ["trainer_id"]
                    }
                }
            },
            "delete_learner": {
                "function": self.crm_repo.delete_learner,
                "schema": {
                    "name": "delete_learner",
                    "description": "Delete a learner from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "learner_id": {
                                "type": "string",
                                "description": "ID of the learner to delete"
                            }
                        },
                        "required": ["learner_id"]
                    }
                }
            },
            "delete_course": {
                "function": self.crm_repo.delete_course,
                "schema": {
                    "name": "delete_course",
                    "description": "Delete a course from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "course_id": {
                                "type": "string",
                                "description": "ID of the course to delete"
                            }
                        },
                        "required": ["course_id"]
                    }
                }
            },
            "update_activity": {
                "function": self.crm_repo.update_activity,
                "schema": {
                    "name": "update_activity",
                    "description": "Update an existing activity's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "activity_id": {
                                "type": "string",
                                "description": "ID of the activity to update"
                            },
                            "activity_name": {
                                "type": "string",
                                "description": "Updated activity name (optional)"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Updated associated lead ID (optional)"
                            },
                            "batch_id": {
                                "type": "integer",
                                "description": "Updated associated batch ID (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Updated associated trainer ID (optional)"
                            },
                            "campaign_id": {
                                "type": "integer",
                                "description": "Updated associated campaign ID (optional)"
                            },
                            "learner_id": {
                                "type": "integer",
                                "description": "Updated associated learner ID (optional)"
                            }
                        },
                        "required": ["activity_id"]
                    }
                }
            },
            "delete_activity": {
                "function": self.crm_repo.delete_activity,
                "schema": {
                    "name": "delete_activity",
                    "description": "Delete an activity from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "activity_id": {
                                "type": "string",
                                "description": "ID of the activity to delete"
                            }
                        },
                        "required": ["activity_id"]
                    }
                }
            },
            "update_note": {
                "function": self.crm_repo.update_note,
                "schema": {
                    "name": "update_note",
                    "description": "Update an existing note's information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "note_id": {
                                "type": "string",
                                "description": "ID of the note to update"
                            },
                            "content": {
                                "type": "string",
                                "description": "Updated content (optional)"
                            },
                            "lead_id": {
                                "type": "integer",
                                "description": "Updated associated lead ID (optional)"
                            },
                            "batch_id": {
                                "type": "integer",
                                "description": "Updated associated batch ID (optional)"
                            },
                            "trainer_id": {
                                "type": "integer",
                                "description": "Updated associated trainer ID (optional)"
                            },
                            "campaign_id": {
                                "type": "integer",
                                "description": "Updated associated campaign ID (optional)"
                            },
                            "learner_id": {
                                "type": "integer",
                                "description": "Updated associated learner ID (optional)"
                            }
                        },
                        "required": ["note_id"]
                    }
                }
            },
            "delete_note": {
                "function": self.crm_repo.delete_note,
                "schema": {
                    "name": "delete_note",
                    "description": "Delete a note from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "note_id": {
                                "type": "string",
                                "description": "ID of the note to delete"
                            }
                        },
                        "required": ["note_id"]
                    }
                }
            },
            "delete_batch": {
                "function": self.crm_repo.delete_batch,
                "schema": {
                    "name": "delete_batch",
                    "description": "Delete a batch from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "batch_id": {
                                "type": "string",
                                "description": "ID of the batch to delete"
                            }
                        },
                        "required": ["batch_id"]
                    }
                }
            },
            "delete_email": {
                "function": self.crm_repo.delete_email,
                "schema": {
                    "name": "delete_email",
                    "description": "Delete an email record from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_id": {
                                "type": "string",
                                "description": "ID of the email to delete"
                            }
                        },
                        "required": ["email_id"]
                    }
                }
            },
            "delete_call": {
                "function": self.crm_repo.delete_call,
                "schema": {
                    "name": "delete_call",
                    "description": "Delete a call record from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "call_id": {
                                "type": "string",
                                "description": "ID of the call to delete"
                            }
                        },
                        "required": ["call_id"]
                    }
                }
            },
            "delete_meeting": {
                "function": self.crm_repo.delete_meeting,
                "schema": {
                    "name": "delete_meeting",
                    "description": "Delete a meeting record from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meeting_id": {
                                "type": "string",
                                "description": "ID of the meeting to delete"
                            }
                        },
                        "required": ["meeting_id"]
                    }
                }
            },
            "delete_message": {
                "function": self.crm_repo.delete_message,
                "schema": {
                    "name": "delete_message",
                    "description": "Delete a message record from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "ID of the message to delete"
                            }
                        },
                        "required": ["message_id"]
                    }
                }
            },
            "create_batch_lead": {
                "function": self.crm_repo.create_batch_lead,
                "schema": {
                    "name": "create_batch_lead",
                    "description": "Create a new batch_lead relationship in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lead_id": {
                                "type": "string",
                                "description": "ID of the lead"
                            },
                            "batch_id": {
                                "type": "string",
                                "description": "ID of the batch"
                            },
                            "status": {
                                "type": "string",
                                "description": "Status of the relationship (optional)"
                            }
                        },
                        "required": ["lead_id", "batch_id"]
                    }
                }
            },
            "update_batch_lead": {
                "function": self.crm_repo.update_batch_lead,
                "schema": {
                    "name": "update_batch_lead",
                    "description": "Update an existing batch_lead relationship.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "batch_lead_id": {
                                "type": "string",
                                "description": "ID of the batch_lead relationship to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)"
                            }
                        },
                        "required": ["batch_lead_id"]
                    }
                }
            },
            "delete_batch_lead": {
                "function": self.crm_repo.delete_batch_lead,
                "schema": {
                    "name": "delete_batch_lead",
                    "description": "Delete a batch_lead relationship from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "batch_lead_id": {
                                "type": "string",
                                "description": "ID of the batch_lead relationship to delete"
                            }
                        },
                        "required": ["batch_lead_id"]
                    }
                }
            },
            "create_learner_batch": {
                "function": self.crm_repo.create_learner_batch,
                "schema": {
                    "name": "create_learner_batch",
                    "description": "Create a new learner_batches relationship in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "learner_id": {
                                "type": "string",
                                "description": "ID of the learner"
                            },
                            "batch_id": {
                                "type": "string",
                                "description": "ID of the batch"
                            },
                            "status": {
                                "type": "string",
                                "description": "Status of the enrollment (optional)"
                            },
                            "enrollment_date": {
                                "type": "string",
                                "description": "Enrollment date (ISO format, optional)"
                            }
                        },
                        "required": ["learner_id", "batch_id"]
                    }
                }
            },
            "update_learner_batch": {
                "function": self.crm_repo.update_learner_batch,
                "schema": {
                    "name": "update_learner_batch",
                    "description": "Update an existing learner_batches relationship.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "learner_batch_id": {
                                "type": "string",
                                "description": "ID of the learner_batch relationship to update"
                            },
                            "status": {
                                "type": "string",
                                "description": "Updated status (optional)"
                            },
                            "completion_date": {
                                "type": "string",
                                "description": "Completion date (ISO format, optional)"
                            }
                        },
                        "required": ["learner_batch_id"]
                    }
                }
            },
            "delete_learner_batch": {
                "function": self.crm_repo.delete_learner_batch,
                "schema": {
                    "name": "delete_learner_batch",
                    "description": "Delete a learner_batches relationship from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "learner_batch_id": {
                                "type": "string",
                                "description": "ID of the learner_batch relationship to delete"
                            }
                        },
                        "required": ["learner_batch_id"]
                    }
                }
            },
            "create_email_template": {
                "function": self.crm_repo.create_email_template,
                "schema": {
                    "name": "create_email_template",
                    "description": "Create a new email template in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Template name"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject template"
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body template"
                            },
                            "template_type": {
                                "type": "string",
                                "description": "Type of template (e.g., 'Welcome', 'Follow-up', 'Reminder')"
                            },
                            "is_active": {
                                "type": "boolean",
                                "description": "Whether the template is active (optional)"
                            }
                        },
                        "required": ["name", "subject", "body"]
                    }
                }
            },
            "update_email_template": {
                "function": self.crm_repo.update_email_template,
                "schema": {
                    "name": "update_email_template",
                    "description": "Update an existing email template.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_template_id": {
                                "type": "string",
                                "description": "ID of the email template to update"
                            },
                            "name": {
                                "type": "string",
                                "description": "Updated name (optional)"
                            },
                            "subject": {
                                "type": "string",
                                "description": "Updated subject (optional)"
                            },
                            "body": {
                                "type": "string",
                                "description": "Updated body (optional)"
                            },
                            "is_active": {
                                "type": "boolean",
                                "description": "Updated active status (optional)"
                            }
                        },
                        "required": ["email_template_id"]
                    }
                }
            },
            "delete_email_template": {
                "function": self.crm_repo.delete_email_template,
                "schema": {
                    "name": "delete_email_template",
                    "description": "Delete an email template from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_template_id": {
                                "type": "string",
                                "description": "ID of the email template to delete"
                            }
                        },
                        "required": ["email_template_id"]
                    }
                }
            },
            "create_message_template": {
                "function": self.crm_repo.create_message_template,
                "schema": {
                    "name": "create_message_template",
                    "description": "Create a new message template in the CRM system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Template name"
                            },
                            "template_type": {
                                "type": "string",
                                "description": "Type of template (e.g., 'SMS', 'WhatsApp', 'Chat')"
                            },
                            "content": {
                                "type": "string",
                                "description": "Template content"
                            },
                            "is_active": {
                                "type": "boolean",
                                "description": "Whether the template is active (optional)"
                            }
                        },
                        "required": ["name", "template_type", "content"]
                    }
                }
            },
            "update_message_template": {
                "function": self.crm_repo.update_message_template,
                "schema": {
                    "name": "update_message_template",
                    "description": "Update an existing message template.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message_template_id": {
                                "type": "string",
                                "description": "ID of the message template to update"
                            },
                            "name": {
                                "type": "string",
                                "description": "Updated name (optional)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Updated content (optional)"
                            },
                            "is_active": {
                                "type": "boolean",
                                "description": "Updated active status (optional)"
                            }
                        },
                        "required": ["message_template_id"]
                    }
                }
            },
            "delete_message_template": {
                "function": self.crm_repo.delete_message_template,
                "schema": {
                    "name": "delete_message_template",
                    "description": "Delete a message template from the CRM system. This is a destructive action and requires confirmation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message_template_id": {
                                "type": "string",
                                "description": "ID of the message template to delete"
                            }
                        },
                        "required": ["message_template_id"]
                    }
                }
            }
        }
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas in OpenAI function calling format."""
        return [tool["schema"] for tool in self.tools.values()]
    
    def get_tool_function(self, tool_name: str):
        """Get the function for a specific tool."""
        if tool_name in self.tools:
            base_function = self.tools[tool_name]["function"]
            
            # Create wrapper functions for update/delete methods that need ID extraction
            if "update_" in tool_name:
                # Extract entity type (e.g., "campaign" from "update_campaign")
                entity_type = tool_name.replace("update_", "")
                entity_id_key = f"{entity_type}_id"
                
                def update_wrapper(arguments: Dict[str, Any]):
                    """Wrapper to extract entity_id and separate update_data."""
                    if entity_id_key not in arguments:
                        raise ValueError(f"Missing required parameter: {entity_id_key}")
                    
                    # Create copy to avoid mutating original
                    arguments_copy = arguments.copy()
                    entity_id = arguments_copy.pop(entity_id_key)
                    update_data = arguments_copy  # Remaining arguments are update_data
                    
                    return base_function(entity_id, update_data)
                
                return update_wrapper
            
            elif "delete_" in tool_name:
                # Extract entity type (e.g., "campaign" from "delete_campaign")
                entity_type = tool_name.replace("delete_", "")
                entity_id_key = f"{entity_type}_id"
                
                def delete_wrapper(arguments: Dict[str, Any]):
                    """Wrapper to extract entity_id."""
                    if entity_id_key not in arguments:
                        raise ValueError(f"Missing required parameter: {entity_id_key}")
                    
                    entity_id = arguments[entity_id_key]
                    return base_function(entity_id)
                
                return delete_wrapper
            
            # For create methods, pass arguments directly (they already accept dict)
            return base_function
        
        return None
    
    def is_destructive_action(self, tool_name: str) -> bool:
        """Check if a tool is a destructive action (requires confirmation)."""
        destructive_tools = [
            "delete_lead", "delete_campaign", "delete_task", "delete_trainer",
            "delete_learner", "delete_course", "delete_activity", "delete_note",
            "delete_batch", "delete_email", "delete_call", "delete_meeting",
            "delete_message", "delete_batch_lead", "delete_learner_batch",
            "delete_email_template", "delete_message_template"
        ]
        return tool_name in destructive_tools
    
    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a tool call before execution.
        Returns (is_valid, error_message)
        """
        if tool_name not in self.tools:
            return False, f"Unknown tool: {tool_name}"
        
        schema = self.tools[tool_name]["schema"]
        required_params = schema["parameters"].get("required", [])
        
        # Check required parameters
        for param in required_params:
            if param not in arguments or arguments[param] is None:
                return False, f"Missing required parameter: {param}"
        
        return True, None

