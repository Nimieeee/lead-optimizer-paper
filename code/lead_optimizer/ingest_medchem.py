
import asyncio
import logging
import json
import re
import os
from uuid import UUID
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.services.vision_service import process_pdf_hybrid
from app.services.text_splitter import text_splitter
from app.services.embeddings import embeddings_service
from app.core.config import settings
from app.core.database import db as db_manager

logger = logging.getLogger(__name__)

# MedChem Knowledge Isolation
MEDCHEM_COLLECTION_ID = UUID("a1b2c3d4-0000-0000-0000-000000000001")
MEDCHEM_USER_ID = UUID("a1b2c3d4-0000-0000-0000-000000000002")

# Category detection keywords
CATEGORY_KEYWORDS = {
    "bioisostere": ["bioisostere", "bioisosteric", "replacement", "isostere",
                    "classical bioisostere", "non-classical", "scaffold hop"],
    "admet_strategy": ["admet", "absorption", "distribution", "metabolism",
                       "excretion", "toxicity", "clearance", "bioavailability", "permeability"],
    "sar_rule": ["structure-activity", "SAR", "pharmacophore", "binding",
                 "affinity", "selectivity", "potency", "interacts with"],
    "structural_alert": ["alert", "toxicophore", "PAINS", "reactive",
                         "mutagenic", "genotoxic", "liability"],
    "pharmacokinetics": ["pharmacokinetic", "half-life", "AUC", "Cmax",
                         "protein binding", "volume of distribution", "t1/2"],
    "toxicology": ["toxicity", "LD50", "hERG", "AMES", "carcinogen",
                   "teratogen", "hepatotox", "cardiotox", "nephrotox"],
}

def detect_category(text: str) -> str:
    """Auto-detect the category of a text chunk based on keywords."""
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[category] = score
    
    if scores:
        return max(scores, key=scores.get)
    return "general"

def detect_chapter(text: str) -> Optional[str]:
    """Detect chapter title from text sample."""
    # Look for patterns like "Chapter 1: ...", "PART I", "1. Introduction"
    patterns = [
        r"(?i)chapter\s+(\d+)\s*[:.-]\s*([^\n]+)",
        r"(?i)part\s+([IVXLCDM]+)\s*[:.-]\s*([^\n]+)",
        r"^\s*(\d+)\.\s+([A-Z][^\n]{5,})"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(0).strip()
    return None

async def ingest_textbook(
    file_path: str,
    checkpoint_file: Optional[str] = None,
    batch_size: int = 100
):
    """
    World-class MedChem textbook ingestion engine.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Textbook not found: {file_path}")
    
    logger.info(f"📚 Starting ingestion: {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
    
    # 1. Load Checkpoint
    start_page = 0
    if checkpoint_file and os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                start_page = checkpoint.get("last_page", 0)
                logger.info(f"🔄 Resuming from page {start_page} via checkpoint")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load checkpoint: {e}")

    # 2. Extract Content (Hybrid Vision/Text)
    # We use process_pdf_hybrid which handles PyMuPDF + Pixtral at 1 req/s
    content = path.read_bytes()
    
    # NOTE: process_pdf_hybrid currently extracts the WHOLE PDF.
    # For textbooks, we might want to iterate page by page ourselves to handle checkpointing better.
    # But for now, we'll use the existing robust hybrid pipeline.
    
    logger.info(f"🧠 Extracting text and vision data from {path.name}...")
    full_text = await process_pdf_hybrid(
        content=content,
        filename=path.name,
        user_prompt="Extract all medicinal chemistry rules, bioisostere tables, and ADMET strategies.",
        api_key=settings.MISTRAL_API_KEY,
        mode="detailed"
    )
    
    logger.info(f"📄 Extraction complete: {len(full_text)} characters")

    # 3. Chunking
    from langchain_core.documents import Document
    doc = Document(
        page_content=full_text,
        metadata={
            "source": path.name,
            "source_type": "medchem_logic",
            "ingestion_date": os.environ.get("CURRENT_DATE", "2026-04-23")
        }
    )
    
    # Use larger chunks for MedChem density
    text_splitter.update_config(chunk_size=1500, chunk_overlap=300)
    chunks = text_splitter.split_documents([doc])
    logger.info(f"✂️ Generated {len(chunks)} high-density chunks")

    # 4. Processing & Embedding
    db = db_manager.get_client()
    bulk_data = []
    
    for i, chunk in enumerate(chunks):
        category = detect_category(chunk.page_content)
        chapter = detect_chapter(chunk.page_content[:500])
        
        chunk.metadata.update({
            "category": category,
            "chapter": chapter or "General",
            "source_type": "medchem_logic",
            "textbook": path.name
        })
        
        # We'll embed them in the next step via batch API
    
    logger.info("🧠 Generating embeddings in batches...")
    chunk_texts = [c.page_content for c in chunks]
    embeddings = await embeddings_service.generate_embeddings_batch(chunk_texts)
    
    expected_dims = settings.EMBEDDING_DIMENSIONS
    for i, chunk in enumerate(chunks):
        emb = embeddings[i]
        if emb and len(emb) == expected_dims:
            bulk_data.append({
                "conversation_id": str(MEDCHEM_COLLECTION_ID),
                "user_id": str(MEDCHEM_USER_ID),
                "content": chunk.page_content,
                "embedding": emb,
                "metadata": chunk.metadata
            })

    # 5. Bulk Insert
    logger.info(f"💾 Storing {len(bulk_data)} chunks in Supabase...")
    inserted_count = 0
    for i in range(0, len(bulk_data), batch_size):
        batch = bulk_data[i : i + batch_size]
        try:
            result = db.table("document_chunks").insert(batch).execute()
            if result.data:
                inserted_count += len(result.data)
                logger.info(f"✅ Inserted {inserted_count}/{len(bulk_data)} chunks...")
        except Exception as e:
            logger.error(f"❌ Batch insert failed at index {i}: {e}")

    logger.info(f"🎉 SUCCESS: Ingested {inserted_count} chunks from {path.name}")
    return inserted_count

if __name__ == "__main__":
    # For direct testing
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        asyncio.run(ingest_textbook(sys.argv[1]))
