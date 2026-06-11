"""
MedChem RAG retrieval tool, callable by the Optimization Agent.
"""

import logging
from typing import Optional, List
from uuid import UUID
from app.services.embeddings import embeddings_service

logger = logging.getLogger(__name__)

MEDCHEM_COLLECTION_ID = UUID("a1b2c3d4-0000-0000-0000-000000000001")
MEDCHEM_USER_ID = UUID("a1b2c3d4-0000-0000-0000-000000000002")

async def query_medchem_db(
    query: str,
    category: Optional[str] = None,
    top_k: int = 8,
    db=None
) -> str:
    """
    Semantic retrieval of medicinal chemistry rules.
    """
    if db is None:
        try:
            from app.core.container import container
            db = container.get_db()
        except Exception:
            from app.core.database import db as db_manager
            db = db_manager.get_client()
    
    # 1. Generate query embedding
    logger.debug(f"DEBUG: query_medchem_db - Generating embedding for: {query[:50]}...")
    query_embedding = await embeddings_service.generate_embedding(query)
    if not query_embedding:
        logger.info("DEBUG: query_medchem_db - FAILED to generate embedding")
        return "ERROR: Failed to generate query embedding"
    
    # 2. Search using pgvector similarity with medchem collection isolation
    logger.debug(f"DEBUG: query_medchem_db - Performing search with ID {MEDCHEM_COLLECTION_ID}...")
    try:
        # Note: Using the specialized RPC for user/conversation isolation
        result = db.rpc(
            'match_documents_with_user_isolation',
            {
                'query_embedding': query_embedding,
                'query_conversation_id': str(MEDCHEM_COLLECTION_ID),
                'query_user_id': str(MEDCHEM_USER_ID),
                'match_threshold': 0.2, # Lower threshold for exploratory medchem search
                'match_count': top_k * 3  # Over-fetch for category filtering
            }
        ).execute()
        
        chunks = result.data or []
        
    except Exception as e:
        logger.error(f"MedChem RAG search failed: {e}")
        return f"ERROR: Database search failed: {str(e)}"
    
    if not chunks:
        return "No relevant medicinal chemistry rules found for this query."
    
    # 3. Filter by category if specified
    if category:
        filtered = [c for c in chunks if c.get('metadata', {}).get('category') == category]
        if filtered:
             chunks = filtered
    
    # 4. Take top_k
    chunks = chunks[:top_k]
    
    # 5. Format results with provenance
    formatted_parts = []
    for i, chunk in enumerate(chunks):
        metadata = chunk.get('metadata', {})
        source = metadata.get('textbook', 'Seed Knowledge')
        cat = metadata.get('category', 'general')
        similarity = chunk.get('similarity', 0)
        content = chunk.get('content', '')
        
        formatted_parts.append(
            f"--- Rule {i+1} (Source: {source}, Category: {cat}, Relevance: {similarity:.2f}) ---\n{content}"
        )
    
    return "\n\n".join(formatted_parts)
