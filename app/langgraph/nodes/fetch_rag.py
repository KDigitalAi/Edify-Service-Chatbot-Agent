from typing import Dict, Any
from app.langgraph.state import AgentState
from app.rag.vector_search import VectorSearch
from app.db.retrieved_context_repo import RetrievedContextRepo
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

async def fetch_rag_node(state: AgentState) -> Dict[str, Any]:
    """
    Fetches RAG data from vector search and attaches to state.
    Persists retrieved data to database.
    """
    try:
        query = state["user_message"]
        session_id = state["session_id"]
        search_engine = VectorSearch()
        
        import time
        retrieval_start = time.time()
        
        # Execute vector search in thread pool if async enabled, otherwise synchronous
        if settings.ENABLE_ASYNC_DB:
            documents = await asyncio.to_thread(search_engine.search, query, 3)
        else:
            documents = search_engine.search(query, limit=3)
        
        retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
        
        # Persist retrieved context to database
        # Optional: Move context saving off main request path using background tasks
        context_repo = RetrievedContextRepo()
        admin_id = state.get("admin_id", "anonymous")
        
        if settings.ENABLE_ASYNC_WRITES:
            # Save context in background task (non-blocking, fire-and-forget)
            async def save_context_async():
                """Save context in background without blocking main request."""
                try:
                    if settings.ENABLE_ASYNC_DB:
                        await asyncio.to_thread(
                            context_repo.save_context,
                            session_id=session_id,
                            admin_id=admin_id,
                            source_type="rag",
                            query_text=query,
                            payload={"data": documents if documents else []},
                            record_count=len(documents) if documents else 0,
                            retrieval_time_ms=retrieval_time_ms
                        )
                    else:
                        context_repo.save_context(
                            session_id=session_id,
                            admin_id=admin_id,
                            source_type="rag",
                            query_text=query,
                            payload={"data": documents if documents else []},
                            record_count=len(documents) if documents else 0,
                            retrieval_time_ms=retrieval_time_ms
                        )
                except Exception as save_error:
                    logger.error(f"Background context save failed: {save_error}", exc_info=True)
            
            # Create background task (fire-and-forget, no await)
            asyncio.create_task(save_context_async())
            logger.debug("Context save scheduled in background task")
        else:
            # Existing sync behavior (blocking)
            if settings.ENABLE_ASYNC_DB:
                await asyncio.to_thread(
                    context_repo.save_context,
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="rag",
                    query_text=query,
                    payload={"data": documents if documents else []},  # Only store retrieved data, not query
                    record_count=len(documents) if documents else 0,
                    retrieval_time_ms=retrieval_time_ms
                )
            else:
                context_repo.save_context(
                    session_id=session_id,
                    admin_id=admin_id,
                    source_type="rag",
                    query_text=query,
                    payload={"data": documents if documents else []},  # Only store retrieved data, not query
                    record_count=len(documents) if documents else 0,
                    retrieval_time_ms=retrieval_time_ms
                )
        
        return {
            "retrieved_context": documents if documents else [],
            "source_type": "rag"
        }
        
    except Exception as e:
        logger.error(f"Error fetching RAG: {e}", exc_info=True)
        # Persist error context
        # Optional: Move error context saving off main request path using background tasks
        try:
            context_repo = RetrievedContextRepo()
            admin_id = state.get("admin_id", "anonymous")
            query = state.get("user_message", "")
            
            if settings.ENABLE_ASYNC_WRITES:
                # Save error context in background task (non-blocking, fire-and-forget)
                async def save_error_context_async():
                    """Save error context in background without blocking main request."""
                    try:
                        if settings.ENABLE_ASYNC_DB:
                            await asyncio.to_thread(
                                context_repo.save_context,
                                session_id=state.get("session_id", "unknown"),
                                admin_id=admin_id,
                                source_type="rag",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                        else:
                            context_repo.save_context(
                                session_id=state.get("session_id", "unknown"),
                                admin_id=admin_id,
                                source_type="rag",
                                query_text=query,
                                payload={"error": str(e)},
                                record_count=0,
                                error_message=str(e)
                            )
                    except Exception as save_error:
                        logger.error(f"Background error context save failed: {save_error}", exc_info=True)
                
                # Create background task (fire-and-forget, no await)
                asyncio.create_task(save_error_context_async())
            else:
                # Existing sync behavior (blocking)
                if settings.ENABLE_ASYNC_DB:
                    await asyncio.to_thread(
                        context_repo.save_context,
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="rag",
                        query_text=query,
                        payload={"error": str(e)},  # Only store error, query is in query_text column
                        record_count=0,
                        error_message=str(e)
                    )
                else:
                    context_repo.save_context(
                        session_id=state.get("session_id", "unknown"),
                        admin_id=admin_id,
                        source_type="rag",
                        query_text=query,
                        payload={"error": str(e)},  # Only store error, query is in query_text column
                        record_count=0,
                        error_message=str(e)
                    )
        except:
            pass
        return {
            "retrieved_context": [],
            "source_type": "rag"
        }
