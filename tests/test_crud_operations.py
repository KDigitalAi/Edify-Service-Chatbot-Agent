"""
Comprehensive CRUD test suite for all database tables.
Tests CREATE, READ, UPDATE, DELETE operations for each table.
Uses cleanup fixtures to ensure no permanent database writes.
"""
import pytest
import uuid
from typing import Dict, Any, List, Optional
from supabase import Client
from tests.conftest import generate_test_data, generate_test_uuid


class CRUDTestResult:
    """Tracks test results for reporting."""
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.create = "SKIP"
        self.read = "SKIP"
        self.update = "SKIP"
        self.delete = "SKIP"
        self.create_error = None
        self.read_error = None
        self.update_error = None
        self.delete_error = None
        self.skip_reason = None


# Global test results tracker
test_results: Dict[str, CRUDTestResult] = {}


def get_or_create_result(table_name: str) -> CRUDTestResult:
    """Gets or creates a test result for a table."""
    if table_name not in test_results:
        test_results[table_name] = CRUDTestResult(table_name)
    return test_results[table_name]


# ============================================================================
# ADMIN_SESSIONS CRUD Tests
# ============================================================================

class TestAdminSessionsCRUD:
    """CRUD tests for admin_sessions table."""
    
    def test_create_admin_session(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test CREATE operation for admin_sessions."""
        table_name = "admin_sessions"
        result = get_or_create_result(table_name)
        
        try:
            session_id = generate_test_uuid()
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                status="active"
            )
            
            response = supabase_client.table(table_name).insert(data).execute()
            
            assert response.data is not None
            assert len(response.data) > 0
            created_record = response.data[0]
            assert created_record["session_id"] == session_id
            assert created_record["admin_id"] == test_admin_id
            assert created_record["status"] == "active"
            
            cleanup_tracker[table_name].append(session_id)
            result.create = "PASS"
            
        except Exception as e:
            result.create = "FAIL"
            result.create_error = str(e)
            raise
    
    def test_read_admin_session(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test READ operation for admin_sessions."""
        table_name = "admin_sessions"
        result = get_or_create_result(table_name)
        
        try:
            # First create a session to read
            session_id = generate_test_uuid()
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table(table_name).insert(data).execute()
            cleanup_tracker[table_name].append(session_id)
            
            # Test READ by ID
            response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("session_id", session_id)
                .single()
                .execute()
            )
            
            assert response.data is not None
            assert response.data["session_id"] == session_id
            assert response.data["admin_id"] == test_admin_id
            
            # Test LIST query
            list_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("admin_id", test_admin_id)
                .execute()
            )
            
            assert list_response.data is not None
            assert len(list_response.data) > 0
            found = any(r["session_id"] == session_id for r in list_response.data)
            assert found, "Created session not found in list query"
            
            result.read = "PASS"
            
        except Exception as e:
            result.read = "FAIL"
            result.read_error = str(e)
            raise
    
    def test_update_admin_session(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test UPDATE operation for admin_sessions."""
        table_name = "admin_sessions"
        result = get_or_create_result(table_name)
        
        try:
            # Create a session
            session_id = generate_test_uuid()
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                status="active"
            )
            supabase_client.table(table_name).insert(data).execute()
            cleanup_tracker[table_name].append(session_id)
            
            # Update the session
            update_data = {"status": "ended"}
            response = (
                supabase_client.table(table_name)
                .update(update_data)
                .eq("session_id", session_id)
                .execute()
            )
            
            assert response.data is not None
            assert len(response.data) > 0
            updated_record = response.data[0]
            assert updated_record["status"] == "ended"
            
            # Verify change persisted
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("session_id", session_id)
                .single()
                .execute()
            )
            assert verify_response.data["status"] == "ended"
            
            result.update = "PASS"
            
        except Exception as e:
            result.update = "FAIL"
            result.update_error = str(e)
            raise
    
    def test_delete_admin_session(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test DELETE operation for admin_sessions."""
        table_name = "admin_sessions"
        result = get_or_create_result(table_name)
        
        try:
            # Create a session
            session_id = generate_test_uuid()
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table(table_name).insert(data).execute()
            
            # Delete the session
            delete_response = (
                supabase_client.table(table_name)
                .delete()
                .eq("session_id", session_id)
                .execute()
            )
            
            # Verify record removed
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("session_id", session_id)
                .execute()
            )
            
            assert verify_response.data is None or len(verify_response.data) == 0
            
            # Don't add to cleanup tracker since we already deleted it
            result.delete = "PASS"
            
        except Exception as e:
            result.delete = "FAIL"
            result.delete_error = str(e)
            # Add to cleanup tracker in case delete failed
            cleanup_tracker[table_name].append(session_id)
            raise


# ============================================================================
# RETRIEVED_CONTEXT CRUD Tests
# ============================================================================

class TestRetrievedContextCRUD:
    """CRUD tests for retrieved_context table."""
    
    def test_create_retrieved_context(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test CREATE operation for retrieved_context."""
        table_name = "retrieved_context"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session first
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create retrieved_context
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                source_type="crm",
                query_text="test query",
                payload={"test": "data"},
                record_count=1
            )
            
            response = supabase_client.table(table_name).insert(data).execute()
            
            assert response.data is not None
            assert len(response.data) > 0
            created_record = response.data[0]
            assert created_record["session_id"] == session_id
            assert created_record["source_type"] == "crm"
            assert created_record["query_text"] == "test query"
            
            cleanup_tracker[table_name].append(created_record["id"])
            result.create = "PASS"
            
        except Exception as e:
            result.create = "FAIL"
            result.create_error = str(e)
            raise
    
    def test_read_retrieved_context(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test READ operation for retrieved_context."""
        table_name = "retrieved_context"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create context record
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                source_type="lms"
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            cleanup_tracker[table_name].append(record_id)
            
            # Test READ by ID
            response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .single()
                .execute()
            )
            
            assert response.data is not None
            assert response.data["id"] == record_id
            assert response.data["session_id"] == session_id
            
            # Test LIST query
            list_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("session_id", session_id)
                .execute()
            )
            
            assert list_response.data is not None
            assert len(list_response.data) > 0
            found = any(r["id"] == record_id for r in list_response.data)
            assert found, "Created record not found in list query"
            
            result.read = "PASS"
            
        except Exception as e:
            result.read = "FAIL"
            result.read_error = str(e)
            raise
    
    def test_update_retrieved_context(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test UPDATE operation for retrieved_context."""
        table_name = "retrieved_context"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create context record
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                record_count=1
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            cleanup_tracker[table_name].append(record_id)
            
            # Update the record
            update_data = {"record_count": 5}
            response = (
                supabase_client.table(table_name)
                .update(update_data)
                .eq("id", record_id)
                .execute()
            )
            
            assert response.data is not None
            assert len(response.data) > 0
            updated_record = response.data[0]
            assert updated_record["record_count"] == 5
            
            # Verify change persisted
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .single()
                .execute()
            )
            assert verify_response.data["record_count"] == 5
            
            result.update = "PASS"
            
        except Exception as e:
            result.update = "FAIL"
            result.update_error = str(e)
            raise
    
    def test_delete_retrieved_context(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test DELETE operation for retrieved_context."""
        table_name = "retrieved_context"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create context record
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            
            # Delete the record
            delete_response = (
                supabase_client.table(table_name)
                .delete()
                .eq("id", record_id)
                .execute()
            )
            
            # Verify record removed
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .execute()
            )
            
            assert verify_response.data is None or len(verify_response.data) == 0
            
            result.delete = "PASS"
            
        except Exception as e:
            result.delete = "FAIL"
            result.delete_error = str(e)
            cleanup_tracker[table_name].append(record_id)
            raise


# ============================================================================
# AUDIT_LOGS CRUD Tests
# ============================================================================

class TestAuditLogsCRUD:
    """CRUD tests for audit_logs table."""
    
    def test_create_audit_log(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test CREATE operation for audit_logs."""
        table_name = "audit_logs"
        result = get_or_create_result(table_name)
        
        try:
            data = generate_test_data(
                table_name,
                admin_id=test_admin_id,
                action="test_action",
                metadata={"key": "value"}
            )
            
            response = supabase_client.table(table_name).insert(data).execute()
            
            assert response.data is not None
            assert len(response.data) > 0
            created_record = response.data[0]
            assert created_record["admin_id"] == test_admin_id
            assert created_record["action"] == "test_action"
            
            cleanup_tracker[table_name].append(created_record["id"])
            result.create = "PASS"
            
        except Exception as e:
            result.create = "FAIL"
            result.create_error = str(e)
            raise
    
    def test_read_audit_log(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test READ operation for audit_logs."""
        table_name = "audit_logs"
        result = get_or_create_result(table_name)
        
        try:
            # Create a log
            data = generate_test_data(
                table_name,
                admin_id=test_admin_id,
                action="read_test"
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            cleanup_tracker[table_name].append(record_id)
            
            # Test READ by ID
            response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .single()
                .execute()
            )
            
            assert response.data is not None
            assert response.data["id"] == record_id
            assert response.data["admin_id"] == test_admin_id
            
            # Test LIST query
            list_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("admin_id", test_admin_id)
                .execute()
            )
            
            assert list_response.data is not None
            assert len(list_response.data) > 0
            found = any(r["id"] == record_id for r in list_response.data)
            assert found, "Created record not found in list query"
            
            result.read = "PASS"
            
        except Exception as e:
            result.read = "FAIL"
            result.read_error = str(e)
            raise
    
    def test_update_audit_log(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test UPDATE operation for audit_logs."""
        table_name = "audit_logs"
        result = get_or_create_result(table_name)
        
        try:
            # Create a log
            data = generate_test_data(
                table_name,
                admin_id=test_admin_id,
                action="update_test",
                metadata={"original": "value"}
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            cleanup_tracker[table_name].append(record_id)
            
            # Update the log
            update_data = {"metadata": {"updated": "value"}}
            response = (
                supabase_client.table(table_name)
                .update(update_data)
                .eq("id", record_id)
                .execute()
            )
            
            assert response.data is not None
            assert len(response.data) > 0
            updated_record = response.data[0]
            assert updated_record["metadata"]["updated"] == "value"
            
            # Verify change persisted
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .single()
                .execute()
            )
            assert verify_response.data["metadata"]["updated"] == "value"
            
            result.update = "PASS"
            
        except Exception as e:
            result.update = "FAIL"
            result.update_error = str(e)
            raise
    
    def test_delete_audit_log(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test DELETE operation for audit_logs."""
        table_name = "audit_logs"
        result = get_or_create_result(table_name)
        
        try:
            # Create a log
            data = generate_test_data(
                table_name,
                admin_id=test_admin_id,
                action="delete_test"
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            
            # Delete the log
            delete_response = (
                supabase_client.table(table_name)
                .delete()
                .eq("id", record_id)
                .execute()
            )
            
            # Verify record removed
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .execute()
            )
            
            assert verify_response.data is None or len(verify_response.data) == 0
            
            result.delete = "PASS"
            
        except Exception as e:
            result.delete = "FAIL"
            result.delete_error = str(e)
            cleanup_tracker[table_name].append(record_id)
            raise


# ============================================================================
# CHAT_HISTORY CRUD Tests
# ============================================================================

class TestChatHistoryCRUD:
    """CRUD tests for chat_history table."""
    
    def test_create_chat_history(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test CREATE operation for chat_history."""
        table_name = "chat_history"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session first
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create chat_history
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                user_message="Hello",
                assistant_response="Hi there",
                source_type="crm"
            )
            
            response = supabase_client.table(table_name).insert(data).execute()
            
            assert response.data is not None
            assert len(response.data) > 0
            created_record = response.data[0]
            assert created_record["session_id"] == session_id
            assert created_record["user_message"] == "Hello"
            assert created_record["assistant_response"] == "Hi there"
            
            cleanup_tracker[table_name].append(created_record["id"])
            result.create = "PASS"
            
        except Exception as e:
            result.create = "FAIL"
            result.create_error = str(e)
            raise
    
    def test_read_chat_history(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test READ operation for chat_history."""
        table_name = "chat_history"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create chat_history record
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                user_message="Test read",
                assistant_response="Test response"
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            cleanup_tracker[table_name].append(record_id)
            
            # Test READ by ID
            response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .single()
                .execute()
            )
            
            assert response.data is not None
            assert response.data["id"] == record_id
            assert response.data["session_id"] == session_id
            
            # Test LIST query
            list_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("session_id", session_id)
                .execute()
            )
            
            assert list_response.data is not None
            assert len(list_response.data) > 0
            found = any(r["id"] == record_id for r in list_response.data)
            assert found, "Created record not found in list query"
            
            result.read = "PASS"
            
        except Exception as e:
            result.read = "FAIL"
            result.read_error = str(e)
            raise
    
    def test_update_chat_history(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test UPDATE operation for chat_history."""
        table_name = "chat_history"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create chat_history record
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                user_message="Original",
                assistant_response="Original response"
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            cleanup_tracker[table_name].append(record_id)
            
            # Update the record
            update_data = {"response_time_ms": 150}
            response = (
                supabase_client.table(table_name)
                .update(update_data)
                .eq("id", record_id)
                .execute()
            )
            
            assert response.data is not None
            assert len(response.data) > 0
            updated_record = response.data[0]
            assert updated_record["response_time_ms"] == 150
            
            # Verify change persisted
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .single()
                .execute()
            )
            assert verify_response.data["response_time_ms"] == 150
            
            result.update = "PASS"
            
        except Exception as e:
            result.update = "FAIL"
            result.update_error = str(e)
            raise
    
    def test_delete_chat_history(self, supabase_client: Client, cleanup_tracker: Dict, test_admin_id: str):
        """Test DELETE operation for chat_history."""
        table_name = "chat_history"
        result = get_or_create_result(table_name)
        
        try:
            # Create parent session
            session_id = generate_test_uuid()
            session_data = generate_test_data(
                "admin_sessions",
                session_id=session_id,
                admin_id=test_admin_id
            )
            supabase_client.table("admin_sessions").insert(session_data).execute()
            cleanup_tracker["admin_sessions"].append(session_id)
            
            # Create chat_history record
            data = generate_test_data(
                table_name,
                session_id=session_id,
                admin_id=test_admin_id,
                user_message="Delete test",
                assistant_response="Delete response"
            )
            insert_response = supabase_client.table(table_name).insert(data).execute()
            record_id = insert_response.data[0]["id"]
            
            # Delete the record
            delete_response = (
                supabase_client.table(table_name)
                .delete()
                .eq("id", record_id)
                .execute()
            )
            
            # Verify record removed
            verify_response = (
                supabase_client.table(table_name)
                .select("*")
                .eq("id", record_id)
                .execute()
            )
            
            assert verify_response.data is None or len(verify_response.data) == 0
            
            result.delete = "PASS"
            
        except Exception as e:
            result.delete = "FAIL"
            result.delete_error = str(e)
            cleanup_tracker[table_name].append(record_id)
            raise


# ============================================================================
# Test Report Generation
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def generate_test_report():
    """Generate test report after all tests complete."""
    yield
    
    print("\n" + "=" * 80)
    print("CRUD TEST REPORT")
    print("=" * 80)
    
    total_tables = len(test_results)
    tested_tables = sum(1 for r in test_results.values() if (
        r.create != "SKIP" or r.read != "SKIP" or r.update != "SKIP" or r.delete != "SKIP"
    ))
    passed_tables = sum(1 for r in test_results.values() if all(
        op in ("PASS", "SKIP") for op in [r.create, r.read, r.update, r.delete]
    ))
    failed_tables = sum(1 for r in test_results.values() if any(
        op == "FAIL" for op in [r.create, r.read, r.update, r.delete]
    ))
    skipped_tables = sum(1 for r in test_results.values() if all(
        op == "SKIP" for op in [r.create, r.read, r.update, r.delete]
    ))
    
    print(f"Total Tables: {total_tables}")
    print(f"Tables Tested: {tested_tables}")
    print(f"Tables Passed: {passed_tables}")
    print(f"Tables Failed: {failed_tables}")
    print(f"Tables Skipped: {skipped_tables}")
    print("\n" + "-" * 80)
    
    for table_name, result in sorted(test_results.items()):
        print(f"\nTABLE: {table_name}")
        print(f"  CREATE: {result.create}")
        if result.create == "FAIL" and result.create_error:
            print(f"    Error: {result.create_error}")
        
        print(f"  READ: {result.read}")
        if result.read == "FAIL" and result.read_error:
            print(f"    Error: {result.read_error}")
        
        print(f"  UPDATE: {result.update}")
        if result.update == "FAIL" and result.update_error:
            print(f"    Error: {result.update_error}")
        
        print(f"  DELETE: {result.delete}")
        if result.delete == "FAIL" and result.delete_error:
            print(f"    Error: {result.delete_error}")
        
        if result.skip_reason:
            print(f"  Skip Reason: {result.skip_reason}")
    
    print("\n" + "=" * 80)

