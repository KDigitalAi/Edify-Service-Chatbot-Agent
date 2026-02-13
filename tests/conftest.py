"""
Pytest configuration and fixtures for CRUD tests.
Provides database client and cleanup utilities.
"""
import pytest
import uuid
from typing import Dict, Any, List
from app.db.supabase import get_chatbot_supabase_client
from supabase import Client


@pytest.fixture(scope="function")
def supabase_client() -> Client:
    """
    Provides a Supabase client for testing.
    Uses the chatbot Supabase database.
    """
    return get_chatbot_supabase_client()


@pytest.fixture(scope="function")
def test_admin_id() -> str:
    """
    Generates a unique test admin ID for each test.
    """
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def cleanup_tracker():
    """
    Tracks created records for cleanup after tests.
    Returns a dict with table names as keys and lists of record IDs as values.
    """
    tracker = {
        "admin_sessions": [],
        "retrieved_context": [],
        "audit_logs": [],
        "chat_history": []
    }
    yield tracker
    
    # Cleanup after test
    client = get_chatbot_supabase_client()
    
    # Delete in reverse dependency order
    # 1. Delete child records first
    for record_id in tracker["chat_history"]:
        try:
            client.table("chat_history").delete().eq("id", record_id).execute()
        except Exception:
            pass
    
    for record_id in tracker["retrieved_context"]:
        try:
            client.table("retrieved_context").delete().eq("id", record_id).execute()
        except Exception:
            pass
    
    for record_id in tracker["audit_logs"]:
        try:
            client.table("audit_logs").delete().eq("id", record_id).execute()
        except Exception:
            pass
    
    # 2. Delete parent records
    for session_id in tracker["admin_sessions"]:
        try:
            client.table("admin_sessions").delete().eq("session_id", session_id).execute()
        except Exception:
            pass


def generate_test_uuid() -> str:
    """Helper to generate test UUIDs."""
    return str(uuid.uuid4())


def generate_test_data(table_name: str, **kwargs) -> Dict[str, Any]:
    """
    Generates test data for a given table.
    Handles required fields and foreign keys.
    """
    base_data = {}
    
    if table_name == "admin_sessions":
        base_data = {
            "session_id": kwargs.get("session_id", generate_test_uuid()),
            "admin_id": kwargs.get("admin_id", generate_test_uuid()),
            "status": kwargs.get("status", "active"),
        }
    
    elif table_name == "retrieved_context":
        base_data = {
            "session_id": kwargs.get("session_id", generate_test_uuid()),
            "admin_id": kwargs.get("admin_id", generate_test_uuid()),
            "source_type": kwargs.get("source_type", "none"),
            "query_text": kwargs.get("query_text", "test query"),
            "payload": kwargs.get("payload", {}),
            "record_count": kwargs.get("record_count", 0),
        }
    
    elif table_name == "audit_logs":
        base_data = {
            "admin_id": kwargs.get("admin_id", generate_test_uuid()),
            "action": kwargs.get("action", "test_action"),
            "metadata": kwargs.get("metadata", {}),
        }
        if "session_id" in kwargs:
            base_data["session_id"] = kwargs["session_id"]
    
    elif table_name == "chat_history":
        base_data = {
            "session_id": kwargs.get("session_id", generate_test_uuid()),
            "admin_id": kwargs.get("admin_id", generate_test_uuid()),
            "user_message": kwargs.get("user_message", "test message"),
            "assistant_response": kwargs.get("assistant_response", "test response"),
        }
        if "source_type" in kwargs:
            base_data["source_type"] = kwargs["source_type"]
    
    # Override with any provided kwargs
    base_data.update(kwargs)
    return base_data

