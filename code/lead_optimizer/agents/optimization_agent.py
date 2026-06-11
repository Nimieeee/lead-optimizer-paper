import asyncio
import json
import logging
from typing import List, Optional
from app.core.config import settings
from ..schemas import OptimizationAgentOutput, VisionAgentOutput, LeadProfile, SmirksStrategy
from ..prompts import OPTIMIZATION_AGENT_SYSTEM_PROMPT, OPTIMIZATION_AGENT_USER_TEMPLATE
from ..smirks_library import SMIRKS_LIBRARY, get_smirks_for_group
from groq import AsyncGroq

try:
    from mistralai import Mistral
    MISTRAL_SDK_AVAILABLE = True
except ImportError:
    MISTRAL_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)

async def run_optimization_agent(
    lead_smiles: str,
    vision_output: VisionAgentOutput,
    lead_profile: LeadProfile,
    user_context: str = "",
    max_selections: int = 30,
    has_lid: bool = True
) -> OptimizationAgentOutput:
    """
    Select bioisosteric replacement strategies from the curated SMIRKS library using direct Groq API.
    """
    # Build context descriptions. Each restricted group may contact multiple
    # residues via multiple interaction types — list them all so the optimizer
    # LLM has the full pharmacophore picture, not just the first contact.
    def _format_restricted(g) -> str:
        residues = g.residues or ([g.residue] if g.residue else [])
        itypes = g.interaction_types or ([g.interaction_type] if g.interaction_type else [])
        if len(residues) <= 1:
            r = residues[0] if residues else "unknown"
            t = itypes[0].value if itypes else "contact"
            return f"- {g.group_name} (interacts with {r} via {t})"
        # Multi-residue: zip residue with its type when aligned, else list all
        contacts = []
        for i, r in enumerate(residues):
            t = itypes[i].value if i < len(itypes) else "contact"
            contacts.append(f"{r}({t})")
        return f"- {g.group_name} (interacts with {', '.join(contacts)})"

    restricted_desc = "\n".join(_format_restricted(g) for g in vision_output.restricted_groups)
    
    target_desc = "\n".join(
        f"- {g.group_name} at {g.position_description}"
        for g in vision_output.target_groups
    )
    
    admet_summary = "\n".join(
        f"- {l.endpoint}: {l.value:.2f} (threshold: {l.threshold}, goal: {l.goal})"
        for l in lead_profile.liabilities
    )
    
    # Build SMIRKS library summary (with token budget management)
    smirks_summaries = []
    
    # 1. Specific matches for target groups — always include these
    for group in vision_output.target_groups:
        available = get_smirks_for_group(group.group_name)
        if available:
            summary = f"\n[Specific SMIRKS for {group.group_name}]:\n"
            for entry in available:
                summary += f"  {entry.id}: {entry.name} — {entry.description}\n"
            smirks_summaries.append(summary)
    
    # 2. General Optimization Library — SMART TRUNCATION to fit token budget
    # Groq Llama 4 Scout limit: ~30,000 input tokens. We budget ~15,000 for SMIRKS.
    # Strategy: include only categories relevant to liabilities + a curated subset
    MAX_SMIRKS_CHARS = 50000  # ~12,500 tokens at 4 chars/token
    
    all_categories = list(set(e.category for e in SMIRKS_LIBRARY.values()))
    liability_keywords = {l.endpoint.lower().replace('_', '') for l in lead_profile.liabilities}
    
    # Score categories by relevance to liabilities
    category_relevance = {}
    for cat in all_categories:
        score = 0
        cat_lower = cat.lower()
        for kw in liability_keywords:
            if 'cyp' in kw and ('metabol' in cat_lower or 'cyp' in cat_lower or 'stability' in cat_lower):
                score += 3
            if 'herg' in kw and ('cardio' in cat_lower or 'toxic' in cat_lower):
                score += 3
            if 'dili' in kw and ('toxic' in cat_lower or 'metabol' in cat_lower):
                score += 3
            if 'ames' in kw and ('toxic' in cat_lower or 'mutagen' in cat_lower):
                score += 3
            if 'bbb' in kw and ('cns' in cat_lower or 'penetration' in cat_lower):
                score += 3
            if 'solub' in kw and ('polar' in cat_lower or 'solub' in cat_lower):
                score += 2
            if kw in cat_lower or cat_lower in kw:
                score += 2
        category_relevance[cat] = score
    
    # Sort: relevant first, then by count
    sorted_categories = sorted(all_categories, key=lambda c: (-category_relevance.get(c, 0), c))
    
    summary = f"\n[General Optimization SMIRKS ({len(all_categories)} categories, {len(SMIRKS_LIBRARY)} total entries — showing relevant categories first)]:\n"
    
    # Add entries category by category until budget is reached
    current_length = len(summary)
    entries_added = 0
    for cat in sorted_categories:
        relevance = category_relevance.get(cat, 0)
        cat_entries = [(eid, e) for eid, e in SMIRKS_LIBRARY.items() if e.category == cat]
        cat_entries.sort(key=lambda x: x[0])
        
        cat_header = f"\n  --- {cat} ({len(cat_entries)} entries, relevance: {relevance}) ---\n"
        if current_length + len(cat_header) > MAX_SMIRKS_CHARS:
            summary += f"\n  ... (truncated, budget reached) ..."
            break
        
        summary += cat_header
        current_length += len(cat_header)
        
        for entry_id, entry in cat_entries:
            line = f"  {entry_id}: {entry.name} — {entry.description}\n"
            if current_length + len(line) > MAX_SMIRKS_CHARS:
                summary += "  ... (remaining entries omitted) ..."
                break
            summary += line
            current_length += len(line)
            entries_added += 1
    
    summary += f"\n  [Total: {entries_added}/{len(SMIRKS_LIBRARY)} entries shown]"
    smirks_summaries.append(summary)
    
    smirks_library_text = "\n".join(smirks_summaries)
    
    # 3. Retrieve Textbook Knowledge (RAG)
    # Target the liabilities and user context
    liability_queries = [l.endpoint for l in lead_profile.liabilities]
    relevant_context = user_context[:200] if user_context else "a drug optimization project"
    rag_query = f"Bioisosteric strategies and medicinal chemistry rules for improving {', '.join(liability_queries)} in {relevant_context}."
    
    from ..medchem_rag import query_medchem_db
    logger.debug(f"DEBUG: OptimizationAgent - Querying MedChem RAG: {rag_query}")
    rag_context = await query_medchem_db(rag_query, top_k=5)
    logger.debug(f"DEBUG: OptimizationAgent - RAG results received. Length: {len(rag_context)}")
    
    # Prepare prompt
    user_prompt = OPTIMIZATION_AGENT_USER_TEMPLATE.format(
        lead_smiles=lead_smiles,
        admet_goal=lead_profile.primary_goal,
        admet_profile_summary=admet_summary,
        restricted_groups_description=restricted_desc,
        target_groups_description=target_desc or "No specific target groups identified. Use ADAPTIVE TARGETING.",
        user_context=user_context or "No additional context provided.",
        smirks_library_summary=smirks_library_text,
        rag_context=rag_context
    )
    
    # Always use Mistral Medium for strategy selection (128K context, reliable)
    logger.debug(f"DEBUG: OptimizationAgent - Using Mistral Medium for strategy selection...")
    try:
        if MISTRAL_SDK_AVAILABLE and settings.MISTRAL_API_KEY:
            client = Mistral(api_key=settings.MISTRAL_API_KEY)
            response = client.chat.complete(
                messages=[
                    {"role": "system", "content": OPTIMIZATION_AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                model="mistral-medium-latest",
                temperature=0.0,
                random_seed=42,
                response_format={"type": "json_object"},
                max_tokens=4000
            )
            content = response.choices[0].message.content
        elif settings.MISTRAL_API_KEY:
            # HTTP fallback
            import requests
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistral-medium-latest",
                    "messages": [
                        {"role": "system", "content": OPTIMIZATION_AGENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0,
                    "random_seed": 42,
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"}
                },
                timeout=120
            )
            content = response.json()["choices"][0]["message"]["content"]
        else:
            raise ValueError("MISTRAL_API_KEY not configured")
        
        parsed = json.loads(content)
        logger.debug(f"DEBUG: OptimizationAgent - Mistral response received successfully")
        
        # Parse strategies
        valid_strategies = []
        strat_key = "selections" if "selections" in parsed else "strategies"
        
        for selection in parsed.get(strat_key, []):
            smirks_id = selection.get('smirks_id', selection.get('id', ''))
            if smirks_id in SMIRKS_LIBRARY:
                entry = SMIRKS_LIBRARY[smirks_id]
                valid_strategies.append(SmirksStrategy(
                    site_index=selection.get("site_index", 0),
                    target_group_name=selection.get("target_group_name", "peripheral"),
                    smirks_id=smirks_id,
                    smirks=entry.smirks,
                    replacement_name=entry.name,
                    rationale=selection.get("rationale", "Bioisosteric replacement"),
                    predicted_impact=selection.get("predicted_impact", "Positive"),
                    confidence=selection.get("confidence", 0.7),
                    rag_source=selection.get("rag_source"),
                ))
        
        logger.debug(f"DEBUG: OptimizationAgent - Selected {len(valid_strategies)} valid strategies")
        return OptimizationAgentOutput(
            admet_goal=parsed.get('admet_goal', 'Optimize ADMET profile'),
            expert_narrative=parsed.get('design_narrative', parsed.get('expert_narrative', parsed.get('rationale', ''))),
            strategies=valid_strategies[:max_selections]
        )
        
    except Exception as e:
        logger.error(f"❌ OptimizationAgent - Mistral failed: {e}. Using fallback strategies only.")
        return OptimizationAgentOutput(admet_goal="Error", strategies=[])
