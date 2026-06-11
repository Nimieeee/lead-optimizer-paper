"""
context_analyzer.py, LLM-driven ADMET priority weighting.
"""

import json
import logging
from typing import Dict, List, Optional
from .schemas import ContextAnalysis, EndpointPriority, ADMETLiability
from groq import AsyncGroq
from app.core.config import settings

logger = logging.getLogger(__name__)

KNOWN_ENDPOINTS = {
    "HIA_Hou", "Caco2_Wang", "BBB_Martins", "logP", "molecular_weight",
    "tpsa", "hERG", "AMES", "DILI", "CYP1A2_Veith", "CYP2C9_Veith",
    "CYP2C19_Veith", "CYP2D6_Veith", "CYP3A4_Veith", "Pgp_Broccatelli",
    "Bioavailability_Ma", "PAMPA_NCATS", "Solubility_AqSolDB", "VDss_Lombardo",
    "PPBR_AZ", "Clearance_Hepatocyte_AZ", "Clearance_Microsome_AZ",
    "Half_Life_Obach", "Skin_Reaction", "ClinTox", "Carcinogens_Lagunin",
    "LD50_Zhu", "Lipinski", "QED", "HydrationFreeEnergy_FreeSolv",
    "Lipophilicity_AstraZeneca", "NR-AR", "NR-AR-LBD", "NR-AhR",
    "NR-Aromatase", "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
    "CYP2C9_Substrate_CarbonMangels", "CYP2D6_Substrate_CarbonMangels",
    "CYP3A4_Substrate_CarbonMangels", "NIH_alert", "PAINS_alert",
    "BRENK_alert", "stereo_centers", "hydrogen_bond_acceptors",
    "hydrogen_bond_donors",
}

KNOWN_STRUCT_KEYS = {
    "hard_stops", "hardstops", "hard_stop_thresholds", "stops",
    "hard_stop_summary", "primary_optimization_goal", "primaryoptimizationgoal",
    "goal", "primary_goal", "therapeutic_constraints", "therapeuticconstraints",
    "scoring_rationale", "scoringrationale", "rationale",
    "endpoint_priorities", "endpointpriorities", "priorities", "weights",
}


def _extract_flat_endpoints(parsed: dict) -> List[dict]:
    """
    Extract endpoint priorities when LLM returns flat JSON like:
    {"BBB_Martins": {"weight": 1.0, "reasoning": "..."}, "hERG": {"weight": 0.8}}
    instead of the expected {"endpoint_priorities": [...]}.
    """
    results = []
    for key, value in parsed.items():
        if key in KNOWN_STRUCT_KEYS or key.lower() in {k.lower() for k in KNOWN_STRUCT_KEYS}:
            continue
        if key in KNOWN_ENDPOINTS:
            try:
                if isinstance(value, dict):
                    weight = float(value.get("weight", 0.5))
                    reasoning = value.get("reasoning", value.get("reason", ""))
                    clinical = value.get("clinical_context", value.get("context", ""))
                elif isinstance(value, (int, float)):
                    weight = float(value)
                    reasoning = f"Weighted {weight} by LLM"
                    clinical = ""
                else:
                    weight_str = str(value).lower()
                    if any(t in weight_str for t in ["critical", "high", "must"]):
                        weight = 0.9
                    elif any(t in weight_str for t in ["important", "should"]):
                        weight = 0.7
                    elif any(t in weight_str for t in ["low", "minor"]):
                        weight = 0.2
                    else:
                        weight = 0.5
                    reasoning = str(value)[:200]
                    clinical = ""

                if weight > 0.0:
                    results.append({
                        "endpoint": key,
                        "weight": weight,
                        "reasoning": reasoning or f"LLM-assigned weight for {key}",
                        "clinical_context": clinical or "Project relevance",
                    })
            except Exception:
                continue
    return results

CONTEXT_ANALYZER_PROMPT = """You are a senior pharmacologist and drug development consultant.

You are configuring the scoring system for a lead optimization pipeline. The user has provided 
their project context below. Based on this context, you must determine which ADMET endpoints 
are most important for THIS SPECIFIC PROJECT and assign relative weights.

AVAILABLE ADMET ENDPOINTS:
- HIA_Hou: Human Intestinal Absorption (0-1, higher = better absorption)
- Caco2_Wang: Caco-2 Permeability (log cm/s, higher = better permeability)
- BBB_Martins: Blood-Brain Barrier penetration (0-1, higher = more penetrant)
- logP: Lipophilicity (optimal range 1-4 for most drugs)
- molecular_weight: Molecular weight (optimal < 500 Da)
- tpsa: Topological Polar Surface Area (optimal 20-140 A^2, < 90 for CNS)
- hERG: hERG channel inhibition / cardiotoxicity risk (0-1, lower = safer)
- AMES: Ames mutagenicity (0-1, lower = safer)
- DILI: Drug-Induced Liver Injury risk (0-1, lower = safer)
- CYP2D6_Veith: CYP2D6 inhibition (0-1, lower = less DDI risk)
- CYP3A4_Veith: CYP3A4 inhibition (0-1, lower = less DDI risk)

YOUR TASK:
1. Read the user's project context carefully.
2. Determine which endpoints are CRITICAL, IMPORTANT, or LOW PRIORITY for this project.
3. Assign a weight (0.0 to 1.0) to each endpoint. Weights do not need to sum to 1.0.
   - 1.0 = absolutely critical for this project
   - 0.7 = very important
   - 0.4 = moderately important
   - 0.1 = low priority but still relevant
   - 0.0 = irrelevant for this project
4. For each weighted endpoint, explain WHY it matters for this therapeutic context.
5. Identify any hard-stop thresholds that should disqualify an analog entirely.

EXAMPLES OF REASONING:
- CNS drug targeting Alzheimer's: BBB_Martins weight=1.0 ("Must cross BBB to reach CNS target"), 
  tpsa weight=0.9 ("TPSA must be <90 for CNS penetration"), hERG weight=0.8 ("Elderly patients 
  on polypharmacy, cardiac safety critical")
- Oral oncology drug: HIA_Hou weight=1.0, CYP3A4_Veith weight=0.9 ("Oncology patients on 
  multiple CYP3A4 substrates"), AMES weight=0.3 ("Lower priority for oncology, therapeutic 
  window accepts some genotoxicity risk")
- Topical dermatology: BBB_Martins weight=0.0 ("Topical, no systemic exposure needed"), 
  HIA_Hou weight=0.1 ("Not orally administered")

OUTPUT: JSON matching the schema exactly."""

async def analyze_project_context(
    user_context: str,
    lead_liabilities: List[ADMETLiability],
    lead_smiles: str,
) -> ContextAnalysis:
    """
    Use Mistral Large to analyze the user's project context and produce
    intelligent endpoint weights for Pareto scoring.
    """
    logger.debug(f"DEBUG: ContextAnalyzer - Started for {lead_smiles}")
    
    # Format liabilities for the LLM safely (handling both objects and dicts)
    liability_items = []
    for l in lead_liabilities:
        try:
            # Handle both dict and object (Pydantic model)
            if isinstance(l, dict):
                endpoint = l.get("endpoint", "unknown")
                value = l.get("value", 0.0)
                threshold = l.get("threshold", 0.0)
                direction = l.get("direction", "unknown")
                goal = l.get("goal", "unknown")
            else:
                endpoint = l.endpoint
                value = l.value
                threshold = l.threshold
                direction = l.direction
                goal = l.goal
                
            liability_items.append(
                f"- {endpoint}: current={value:.2f}, threshold={threshold}, "
                f"direction={direction}, goal={goal}"
            )
        except Exception as e:
            logger.debug(f"DEBUG: ContextAnalyzer - Error formatting liability: {e}")
            
    liability_desc = "\n".join(liability_items)
    
    user_message = f"""PROJECT CONTEXT FROM USER:
{user_context or "No specific context provided. Assume general oral drug optimization."}

LEAD COMPOUND: {lead_smiles}

IDENTIFIED ADMET LIABILITIES:
{liability_desc or "No liabilities detected."}

Based on the project context and identified liabilities, assign endpoint weights 
and explain your reasoning for this specific therapeutic program."""
    
    logger.debug(f"DEBUG: ContextAnalyzer - Sending direct prompt to Groq (GPT-OSS 120B) for {lead_smiles}...")
    from groq import AsyncGroq
    from app.core.config import settings
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    primary_model = "openai/gpt-oss-120b"
    fallback_model = "llama-3.3-70b-versatile"
    fallback_used = False

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": CONTEXT_ANALYZER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            model=primary_model,
            temperature=0.2,
            seed=42,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        logger.debug(f"DEBUG: ContextAnalyzer - Received response from Groq. Length: {len(content)}")

        if not content or not content.strip():
            logger.debug(f"DEBUG: ContextAnalyzer - Primary model returned empty. Trying fallback model...")
            fallback_used = True
            response = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": CONTEXT_ANALYZER_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                model=fallback_model,
                temperature=0.2,
                seed=42,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            logger.debug(f"DEBUG: ContextAnalyzer - Fallback model response. Length: {len(content)}")

        parsed = json.loads(content)
        logger.debug(f"DEBUG: ContextAnalyzer - Parsed JSON keys: {list(parsed.keys())}")
        
        # Robust key mapping
        priorities_key = next((k for k in parsed.keys() if k.lower() in ["endpoint_priorities", "endpointpriorities", "priorities", "weights"]), "endpoint_priorities")
        goal_key = next((k for k in parsed.keys() if k.lower() in ["primary_optimization_goal", "primaryoptimizationgoal", "goal"]), "primary_optimization_goal")
        constraints_key = next((k for k in parsed.keys() if k.lower() in ["therapeutic_constraints", "therapeuticconstraints", "constraints"]), "therapeutic_constraints")
        rationale_key = next((k for k in parsed.keys() if k.lower() in ["scoring_rationale", "scoringrationale", "rationale"]), "scoring_rationale")
        stops_key = next((k for k in parsed.keys() if k.lower() in ["hard_stops", "hardstops", "stops", "hard_stop_thresholds", "hardstops", "hard_stop_summary"]), "hard_stops")
        
        from .admet_metadata import ADMET_METADATA, get_endpoint_direction
        
        # Construct priorities with universal extraction
        priorities = []
        raw_priorities = parsed.get(priorities_key, [])
        
        if isinstance(raw_priorities, dict):
            for k, v in raw_priorities.items():
                try:
                    priorities.append(EndpointPriority(
                        endpoint=k, 
                        weight=0.8 if "high" in str(v).lower() else 0.5,
                        direction=get_endpoint_direction(k), 
                        reasoning=f"LLM-suggested priority: {v}", 
                        clinical_context="Project relevance"
                    ))
                except: continue
        elif isinstance(raw_priorities, list):
            for ep in raw_priorities:
                try:
                    if isinstance(ep, str):
                        priorities.append(EndpointPriority(
                            endpoint=ep, weight=0.7, direction=get_endpoint_direction(ep), 
                            reasoning="Direct mention", clinical_context="Clinical focus"
                        ))
                    elif isinstance(ep, dict):
                        ep_name = ep.get("endpoint", "unknown")
                        priorities.append(EndpointPriority(
                            endpoint=ep_name,
                            weight=float(ep.get("weight", 0.7)),
                            direction=get_endpoint_direction(ep_name),
                            reasoning=ep.get("reasoning", "LLM-suggested"),
                            clinical_context=ep.get("clinical_context", "Clinical importance")
                        ))
                except: continue
        
        # FALLBACK: If no priorities found, check for flat JSON structure
        # e.g. {"BBB_Martins": {"weight": 1.0, "reasoning": "..."}, "hERG": {...}}
        if not priorities:
            flat_endpoints = _extract_flat_endpoints(parsed)
            if flat_endpoints:
                for ep_data in flat_endpoints:
                    try:
                        priorities.append(EndpointPriority(
                            endpoint=ep_data["endpoint"],
                            weight=ep_data["weight"],
                            direction=get_endpoint_direction(ep_data["endpoint"]),
                            reasoning=ep_data["reasoning"],
                            clinical_context=ep_data["clinical_context"],
                        ))
                    except: continue
                logger.debug(f"DEBUG: ContextAnalyzer - Flat JSON fallback extracted {len(priorities)} endpoints")

        analysis = ContextAnalysis(
            endpoint_priorities=priorities,
            primary_optimization_goal=parsed.get(goal_key, "General Potency Optimization"),
            therapeutic_constraints=parsed.get(constraints_key, []),
            scoring_rationale=f"Automated analysis (fallback_model={fallback_model})" if fallback_used else parsed.get(rationale_key, "Automated analysis"),
            hard_stops=parsed.get(stops_key, {}),
        )
        logger.debug(f"DEBUG: ContextAnalyzer - Successfully constructed {len(priorities)} priorities")
        logger.debug(f"DEBUG: ContextAnalyzer - Model used: {'GPT-OSS-120B' if not fallback_used else fallback_model}")
        return analysis

    except Exception as e:
        logger.error(f"❌ ContextAnalyzer - Fatal failure: {e}")
        try:
            logger.debug(f"DEBUG: ContextAnalyzer - Attempting fallback model: {fallback_model}")
            fallback_used = True
            response = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": CONTEXT_ANALYZER_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                model=fallback_model,
                temperature=0.2,
                seed=42,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if content and content.strip():
                parsed = json.loads(content)
                priorities = []
                raw_priorities = parsed.get(priorities_key, [])
                from .admet_metadata import ADMET_METADATA, get_endpoint_direction
                if isinstance(raw_priorities, dict):
                    for k, v in raw_priorities.items():
                        try:
                            priorities.append(EndpointPriority(
                                endpoint=k,
                                weight=0.8 if "high" in str(v).lower() else 0.5,
                                direction=get_endpoint_direction(k),
                                reasoning=f"LLM-suggested priority: {v}",
                                clinical_context="Project relevance"
                            ))
                        except: continue
                elif isinstance(raw_priorities, list):
                    for ep in raw_priorities:
                        try:
                            if isinstance(ep, str):
                                priorities.append(EndpointPriority(
                                    endpoint=ep, weight=0.7, direction=get_endpoint_direction(ep),
                                    reasoning="Direct mention", clinical_context="Clinical focus"
                                ))
                            elif isinstance(ep, dict):
                                ep_name = ep.get("endpoint", "unknown")
                                priorities.append(EndpointPriority(
                                    endpoint=ep_name,
                                    weight=float(ep.get("weight", 0.7)),
                                    direction=get_endpoint_direction(ep_name),
                                    reasoning=ep.get("reasoning", "LLM-suggested"),
                                    clinical_context=ep.get("clinical_context", "Clinical importance")
                                ))
                        except: continue

                # FALLBACK: Flat JSON extraction in fallback model too
                if not priorities:
                    flat_endpoints = _extract_flat_endpoints(parsed)
                    if flat_endpoints:
                        for ep_data in flat_endpoints:
                            try:
                                priorities.append(EndpointPriority(
                                    endpoint=ep_data["endpoint"],
                                    weight=ep_data["weight"],
                                    direction=get_endpoint_direction(ep_data["endpoint"]),
                                    reasoning=ep_data["reasoning"],
                                    clinical_context=ep_data["clinical_context"],
                                ))
                            except: continue

                logger.debug(f"DEBUG: ContextAnalyzer - Fallback succeeded, {len(priorities)} priorities")
                return ContextAnalysis(
                    endpoint_priorities=priorities,
                    primary_optimization_goal=parsed.get(goal_key, "General Potency Optimization"),
                    therapeutic_constraints=parsed.get(constraints_key, []),
                    scoring_rationale=f"Automated analysis (fallback_model={fallback_model})",
                    hard_stops=parsed.get(stops_key, {}),
                )
        except Exception as e2:
            logger.error(f"❌ ContextAnalyzer - Fallback also failed: {e2}")
        return ContextAnalysis(
            endpoint_priorities=[],
            primary_optimization_goal="General Potency Optimization",
            therapeutic_constraints=["Safety first"],
            scoring_rationale=f"Fallback due to error: {e}",
            hard_stops={}
        )
