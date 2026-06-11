"""
Dynamic ADMET Profiler, Automatically identifies liabilities from a lead compound.
"""

import httpx
import logging
from typing import Dict, List
from .schemas import ADMETLiability, LeadProfile

logger = logging.getLogger(__name__)
logger.debug("profiler.py module loading...")

ADMET_ENGINE_URL = "http://localhost:8000/admet" # Adjusted to match the Benchside API path

from .admet_metadata import ADMET_METADATA as ADMET_THRESHOLDS

async def profile_lead_compound(lead_smiles: str) -> LeadProfile:
    """
    Run full ADMET profile on the lead compound.
    """
    # Call internal ADMET service
    from app.core.container import container
    admet_service = container.get("admet_service")
    logger.debug(f"DEBUG: Profiler - Retrieved service: {type(admet_service)}")
    
    try:
        # Get predictions for single smiles
        logger.debug(f"DEBUG: Profiler - Calling predict_admet for {lead_smiles}...")
        admet_data = await admet_service.predict_admet(lead_smiles)
        logger.debug(f"DEBUG: Profiler - Raw data type: {type(admet_data)}")
        logger.debug(f"DEBUG: Profiler - Raw data: {admet_data}")
        
        if not admet_data:
            raise RuntimeError("ADMET service returned no results")
        
    except Exception as e:
        logger.error(f"ADMET profiling failed: {e}")
        raise
    
    liabilities = []
    strengths = []
    
    for endpoint, config in ADMET_THRESHOLDS.items():
        value = admet_data.get(endpoint)
        if value is None:
            continue
        
        label = config["label"]
        direction = config["direction"]
        
        if direction == "increase":
            threshold = config["threshold"]
            if value < threshold:
                goal = f"Increase {label} from {value:.2f} to >{threshold}"
                liabilities.append(ADMETLiability(
                    endpoint=endpoint, value=value, threshold=threshold,
                    goal=goal, direction="increase"
                ))
            else:
                strengths.append(f"Good {label} ({value:.2f})")
                
        elif direction == "reduce":
            threshold = config.get("threshold", config.get("max", 0.5))
            if value > threshold:
                goal = f"Reduce {label} from {value:.2f} to <{threshold}"
                liabilities.append(ADMETLiability(
                    endpoint=endpoint, value=value, threshold=threshold,
                    goal=goal, direction="reduce"
                ))
            else:
                strengths.append(f"Low {label} ({value:.2f})")
    
    logger.debug(f"DEBUG: Profiler - Loop complete. {len(liabilities)} liabilities, {len(strengths)} strengths")
    liabilities.sort(key=lambda l: abs(l.value - l.threshold), reverse=True)
    primary_goal = liabilities[0].goal if liabilities else "No liabilities detected, general optimization"
    logger.debug(f"DEBUG: Profiler - Primary goal identified: {primary_goal}")
    
    # ── GASA Synthetic Accessibility ────────────────────────────
    logger.info("DEBUG: Profiler - Running GASA prediction...")
    try:
        from app.services.gasa_service import gasa_predictor
        gasa_result = gasa_predictor.predict_single(lead_smiles)
        if gasa_result:
            admet_data["GASA"] = gasa_result
            logger.debug(f"DEBUG: Profiler - GASA result: {gasa_result}")
        else:
            # Fallback to simple GASA
            from app.services.simple_gasa_service import simple_gasa_predictor
            simple_result = simple_gasa_predictor.predict_single(lead_smiles)
            if simple_result:
                admet_data["GASA"] = simple_result
                logger.debug(f"DEBUG: Profiler - Simple GASA result: {simple_result}")
    except Exception as gasa_err:
        logger.warning(f"⚠️ Profiler - GASA failed (non-critical): {gasa_err}")
    
    logger.info("DEBUG: Profiler - Constructing LeadProfile object...")
    try:
        profile = LeadProfile(
            smiles=lead_smiles,
            admet_data=admet_data,
            liabilities=liabilities,
            strengths=strengths,
            primary_goal=primary_goal
        )
        logger.info("DEBUG: Profiler - LeadProfile constructed successfully")
        return profile
    except Exception as e:
        logger.error(f"❌ Profiler - LeadProfile construction failed: {e}")
        # Return a fallback profile to keep the pipeline alive
        return LeadProfile(
            smiles=lead_smiles,
            admet_data={},
            liabilities=[],
            strengths=[],
            primary_goal="General Optimization"
        )
