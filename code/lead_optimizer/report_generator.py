import os
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from rdkit import Chem
from rdkit.Chem import AllChem
from groq import AsyncGroq
from .schemas import LeadProfile, VisionAgentOutput, ContextAnalysis
from app.core.config import settings

logger = logging.getLogger(__name__)

from rdkit.Chem import Draw
from rdkit.Chem.Draw import rdMolDraw2D
import base64
from io import BytesIO

# -------------------------------------------------------------------
# Synthetic-accessibility display helpers, unified on SYBA primary.
#
# Background: the platform exposed three synth-accessibility metrics
# (Ertl SAScore on a 1–10 scale, GASA hard_probability as a percentage,
# and a normalized-SAScore in the studio property table). Users
# couldn't tell which to trust, and the metrics sometimes pointed in
# opposite directions for sp3-rich analogs of planar aromatic leads.
#
# Resolution: standardize on SYBA across the whole platform, both
# the lead optimizer report AND the ADMET engine display. SYBA is
# signed (positive = Easy, negative = Hard); it was already chosen
# as the primary classifier in synth_accessibility_service.py.
# SAScore (Ertl) is still computed and persisted in the analog
# record for audit / cross-check, but is NOT rendered.
# -------------------------------------------------------------------
def _syba_label(syba_score: Optional[float]) -> str:
    """Return 'Easy' / 'Borderline' / 'Hard' for a signed SYBA score."""
    if syba_score is None:
        return ","
    if syba_score > 5:
        return "Easy"
    if syba_score < -5:
        return "Hard"
    return "Borderline"


def _syba_render(syba_score: Optional[float]) -> str:
    """Plain-text inline rendering used in tables: 'Synth: +12.3 (Easy)'."""
    if syba_score is None:
        return ","
    sign = "+" if syba_score >= 0 else ""
    return f"Synth: {sign}{syba_score:.1f} ({_syba_label(syba_score)})"


def _syba_block(syba_score: Optional[float], sa_score: Optional[float] = None) -> str:
    """HTML block used in the lead-profile section.

    Renders only SYBA; the legacy Ertl SAScore parameter is accepted for
    backward compatibility but is no longer surfaced in the user-visible
    output (it stays in the audit log + the analog records' raw fields).
    """
    if syba_score is None:
        # Fallback only when SYBA is unavailable (model load failure).
        # Render Ertl SAScore but label it clearly so the user knows
        # they're seeing the fallback, not the primary.
        if sa_score is None:
            return ""
        return (
            f'<h4 style="color: #D7712A; margin: 0.4cm 0 0.2cm 0; font-size: 10pt;">'
            f'Synthetic Accessibility</h4>'
            f'<span class="admet-tag tag-neutral">SAScore (fallback): {sa_score:.2f}/10</span>'
        )
    label = _syba_label(syba_score)
    sign = "+" if syba_score >= 0 else ""
    return (
        f'<h4 style="color: #D7712A; margin: 0.4cm 0 0.2cm 0; font-size: 10pt;">'
        f'Synthetic Accessibility</h4>'
        f'<span class="admet-tag tag-neutral">SYBA: {sign}{syba_score:.1f} ({label})</span>'
    )


def _syba_short(gasa: Dict, fallback: str = ",") -> str:
    """One-cell rendering for the comparative table / trading card."""
    if not isinstance(gasa, dict):
        return fallback
    syba = gasa.get("syba_score")
    if syba is not None:
        sign = "+" if syba >= 0 else ""
        return f"{sign}{syba:.1f} ({_syba_label(syba)})"
    # Fallback when SYBA unavailable, show Ertl SAScore clearly labelled.
    sa = gasa.get("sa_score")
    if sa is not None:
        return f"{sa:.1f}/10 (Ertl fallback)"
    return fallback


def _mol_to_base64(smiles: str, size=(300, 300)) -> str:
    """Generate a base64 encoded PNG for a SMILES string."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            img = Draw.MolToImage(mol, size=size)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        logger.error(f"Drawing failed for {smiles}: {e}")
    return ""

def calculate_analog_changes(analog: Dict, lead_profile: LeadProfile) -> Dict:
    """Calculate liability and strength changes for an analog vs lead."""
    admet = analog.get("admet_results", {})
    changes = {
        'liabilities': [],
        'strengths': []
    }
    
    for liab in lead_profile.liabilities:
        endpoint = liab.endpoint
        lead_val = liab.value
        analog_val = admet.get(endpoint, lead_val)
        delta = analog_val - lead_val
        pct = ((analog_val - lead_val) / lead_val * 100) if lead_val != 0 else 0
        
        # Determine if improvement
        improved = False
        if liab.direction == 'reduce':
            improved = analog_val < lead_val
        else:
            improved = analog_val > lead_val
            
        changes['liabilities'].append({
            'endpoint': endpoint,
            'lead': lead_val,
            'analog': analog_val,
            'delta': delta,
            'pct': pct,
            'improved': improved,
            'direction': liab.direction
        })
    
    # Parse strengths from lead_profile.strengths
    for s in lead_profile.strengths:
        # Try to extract endpoint from strength string
        # Format: "Good Absorption (HIA) (1.00)" or "Low hERG Risk (0.15)"
        import re
        match = re.match(r'.*?\(([^)]+)\)\s*\(([^)]+)\)', s)
        if match:
            endpoint = match.group(1)
            lead_val = float(match.group(2))
            analog_val = admet.get(endpoint, lead_val)
            delta = analog_val - lead_val
            pct = ((analog_val - lead_val) / lead_val * 100) if lead_val != 0 else 0
            
            # For strengths, we want to maintain or improve
            # If it's a "good" thing (high value), decrease is bad
            # If it's a "low" thing (low value), increase is bad
            is_low = s.lower().startswith('low')
            improved = (analog_val < lead_val) if is_low else (analog_val >= lead_val)
            
            changes['strengths'].append({
                'endpoint': endpoint,
                'label': s,
                'lead': lead_val,
                'analog': analog_val,
                'delta': delta,
                'pct': pct,
                'improved': improved
            })
    
    return changes

async def fetch_pubmed_citations(modifications: List[str]) -> Dict[str, List[Dict]]:
    """Fetch PubMed citations for each modification."""
    try:
        from app.services.tools import BiomedicalTools
        tools = BiomedicalTools()
        citations = {}
        
        for mod in modifications[:3]:  # Limit to first 3 modifications
            # Create search query
            query = f"{mod} bioisosteric replacement medicinal chemistry"
            results = await tools.fetch_pubmed_literature(query, max_results=2)
            articles = results.get('articles', [])
            
            citations[mod] = [
                {
                    'title': art.get('title', ''),
                    'authors': art.get('authors', ''),
                    'journal': art.get('journal', ''),
                    'year': art.get('year', ''),
                    'pmid': art.get('pmid', ''),
                    'doi': art.get('doi', '')
                }
                for art in articles[:2]  # Top 2 papers per modification
            ]
        
        return citations
    except Exception as e:
        logger.warning(f"PubMed citation fetch failed: {e}")
        return {}

async def generate_report_narrative(
    pipeline_data: dict,
    user_context: str,
    top_analogs: List[Dict],
    lead_profile: LeadProfile
) -> str:
    """
    Generate PhD-grade narrative with PubMed citations and per-analog improvements.
    """
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    
    # Calculate improvements for top 5 analogs
    analog_improvements = []
    for a in top_analogs[:5]:
        changes = calculate_analog_changes(a, lead_profile)
        analog_improvements.append({
            'rank': a.get('pareto_rank', 0),
            'modifications': a.get('modifications', []),
            'score': a.get('pareto_score', 0),
            'liability_changes': [
                {'endpoint': c['endpoint'], 'delta': round(c['delta'], 3), 'pct': round(c['pct'], 1)}
                for c in changes['liabilities']
            ],
            'strength_changes': [
                {'endpoint': c['endpoint'], 'delta': round(c['delta'], 3), 'pct': round(c['pct'], 1)}
                for c in changes['strengths']
            ]
        })
    
    prompt = f"""
    You are writing a PhD-grade scientific report on a lead optimization campaign.
    Write detailed, publication-quality prose explaining the discovery strategy and results.
    
    CRITICAL REQUIREMENTS:
    1. Address the multi-objective nature of the optimization
    2. Explain how each structural modification addresses specific liabilities
    3. Discuss which analogs best balance liability reduction with strength preservation
    4. Cite relevant medicinal chemistry principles where appropriate
    5. Use quantitative data from the improvement summaries
    
    PROJECT CONTEXT:
    {user_context}
    
    LEAD COMPOUND PROFILE:
    - Liabilities: {json.dumps([{'endpoint': l.endpoint, 'value': l.value, 'direction': l.direction} for l in lead_profile.liabilities], indent=2)}
    - Strengths: {json.dumps(lead_profile.strengths, indent=2)}
    
    TOP ANALOG IMPROVEMENTS:
    {json.dumps(analog_improvements, indent=2)}
    
    Write 800-1200 words of flowing academic prose. Include:
    - Introduction to the lead compound and its liabilities
    - Design strategy rationale for structural modifications
    - Analysis of top-performing analogs with quantitative comparisons
    - Discussion of multi-objective trade-offs
    - Conclusions and recommendations for next steps
    
    Format with proper paragraphs. Use specific numbers from the data.
    """
    
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ ReportGenerator - Narrative failed: {e}")
        return "Narrative generation failed. Please review the structural data and ADMET results in the table below."

def _generate_sdf(analogs: List[Dict], output_path: str, lead_smiles: str):
    """Export analogs as SDF with properties."""
    writer = Chem.SDWriter(output_path)
    for i, analog in enumerate(analogs):
        mol = Chem.MolFromSmiles(analog["smiles"])
        if mol is None: continue
        AllChem.Compute2DCoords(mol)
        
        modifications = analog.get("modifications", [])
        rank = analog.get("pareto_rank", i + 1)
        if modifications and modifications[0]:
            name = f"Analog_{rank:02d}_{modifications[0][:50]}"
        else:
            name = f"Analog_{rank:02d}"
        mol.SetProp("_Name", name)
        
        mol.SetProp("SMILES", analog["smiles"])
        mol.SetProp("LeadSMILES", lead_smiles)
        mol.SetProp("Modifications", "; ".join(modifications))
        mol.SetProp("Pareto_Score", f"{analog.get('pareto_score', 0):.4f}")
        mol.SetProp("Pareto_Rank", str(rank))
        admet = analog.get("admet_results", {})
        if admet:
            for key, value in admet.items():
                if isinstance(value, (int, float)):
                    mol.SetProp(f"ADMET_{key}", f"{value:.4f}")
        writer.write(mol)
    writer.close()

async def generate_report(
    lead_smiles: str,
    lead_profile: LeadProfile,
    top_analogs: List[Dict],
    vision_output: VisionAgentOutput,
    user_context: str,
    context_analysis: ContextAnalysis,
    expert_narrative: Optional[str] = None,
    used_lid: bool = False,
    secondary_targets: List[Dict] = None,  # type: ignore
    search_space_size: int = 0,
    methodology_notes: str = "",
    lead_sa_score: Optional[float] = None,   # legacy Ertl SAScore, kept for compat, not displayed
    lead_syba_score: Optional[float] = None  # primary synth metric (signed: + easier, − harder)
) -> Dict[str, str]:
    """
    Generate PDF and SDF reports with PubMed citations.
    """
    # Handle None defaults
    if secondary_targets is None:
        secondary_targets = []
    
    base_dir = Path(__file__).parent.parent.parent.parent
    report_dir = base_dir / "data" / "reports"
    os.makedirs(report_dir, exist_ok=True)
    
    task_id = "report_" + str(hash(lead_smiles))[:8]
    
    # 1. Prepare Structures for ALL analogs
    lead_img = _mol_to_base64(lead_smiles, size=(400, 400))
    for a in top_analogs:
        a["img_base64"] = _mol_to_base64(a["smiles"])
        a["changes"] = calculate_analog_changes(a, lead_profile)
    
    # 2. Fetch PubMed citations for top analogs (limit to save API calls)
    logger.info("📚 Fetching PubMed citations for top analogs...")
    all_modifications = []
    for a in top_analogs[:10]:
        all_modifications.extend(a.get('modifications', []))
    unique_mods = list(set(all_modifications))[:5]  # Unique mods, limit 5
    pubmed_citations = await fetch_pubmed_citations(unique_mods)
    
    # 3. Prepare Narrative
    logger.info("📝 Generating report narrative...")
    strategy_narrative = await generate_report_narrative(
        {}, user_context, top_analogs, lead_profile
    )
    
    if expert_narrative:
        narrative = f"{strategy_narrative}\n\n<h3>Expert Agent Rationale</h3>\n{expert_narrative}"
    else:
        narrative = strategy_narrative
    
    # 4. Create HTML, landscape A4 with elite typography + brand palette.
    # ~28 cm horizontal width fits side-by-side structure + property panel
    # without cramping. Page numbers + section headers via @page rules.
    from datetime import datetime as _dt
    generated_date = _dt.now().strftime("%B %d, %Y")
    css_template = """
    /* @page rules simplified (2026-06-09): WeasyPrint asserted
       page_is_empty when `@page :first { margin: 0 }` combined with
       page-break-after on the cover. A single @page rule with uniform
       margins is more robust; we lose the footer on the cover but
       the styled inner-page content remains intact. */
    @page {
        size: A4 landscape;
        margin: 1.5cm 1.8cm;
    }

    body {
        font-family: 'Inter', 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
        color: #1e293b;
        line-height: 1.55;
        background: #ffffff;
        font-size: 9.5pt;
    }

    /* ── Cover page ──────────────────────────────────────────────────── */
    /* WeasyPrint compatibility notes (2026-06-09):
       - `100vh` is a viewport unit; print has no viewport. Use cm.
       - `clip-path: polygon(...)` not supported, replaced with a
         simpler skewed border via a CSS gradient mask.
       - `backdrop-filter: blur(...)` not supported, drop the effect;
         the white background already provides separation.
       - `display: flex` works in WeasyPrint 60+ for basic stacking;
         keep flex for column layouts but avoid `justify-content`
         edge cases. */
    .cover {
        position: relative;
        width: 100%;
        padding: 4cm 3cm 3cm 3cm;
        /* WeasyPrint assertion fix (2026-06-09): the previous .cover-band
           overlay was a `position: absolute` element. WeasyPrint's
           "in-flow rendering didn't progress, only out-of-flow did"
           branch fires page_is_empty when the cover has the absolute
           overlay BEFORE any in-flow content has measured. Solution:
           inline the band as a background-image layer on .cover itself.
           No layout DOM element, no out-of-flow, no assertion. */
        background:
            linear-gradient(125deg, transparent 0%, transparent 70%, rgba(215,113,42,0.92) 70%, rgba(194,84,32,0.92) 100%) top right / 60% 6cm no-repeat,
            linear-gradient(135deg, #fff8f1 0%, #ffffff 50%, #fff5e8 100%);
    }
    /* .cover-band, REMOVED. Its visual is now a background layer on .cover.
       Keep an empty rule for backwards-compat if the HTML still has the div. */
    .cover-band { display: none; }
    .cover-brand {
        position: relative; z-index: 2;
        font-family: 'Fraunces', Georgia, serif;
        font-size: 13pt;
        font-weight: 600;
        color: #1e293b;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }
    .cover-title {
        position: relative; z-index: 2;
        margin-top: 1cm;
    }
    .cover-title h1 {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 42pt;
        font-weight: 300;
        line-height: 1.05;
        color: #1e293b;
        margin: 0 0 0.3cm 0;
        letter-spacing: -0.01em;
    }
    .cover-title .subtitle {
        font-size: 12pt;
        color: #475569;
        max-width: 16cm;
        font-weight: 400;
    }
    .cover-lead {
        position: relative; z-index: 2;
        display: flex;
        gap: 1cm;
        align-items: center;
        margin-top: 1.5cm;
        padding: 1cm;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 14px;
        border: 1px solid #f1d6b3;
        /* backdrop-filter removed, WeasyPrint doesn't support it; the
           opaque white background provides the separation. */
    }
    .cover-lead-img {
        width: 7cm; height: 7cm;
        background: #ffffff;
        border-radius: 10px;
        border: 1px solid #f3e8d8;
        padding: 0.5cm;
        flex-shrink: 0;
    }
    .cover-lead-img img { width: 100%; height: 100%; object-fit: contain; }
    .cover-lead-meta {
        flex: 1;
        min-width: 0;
    }
    .cover-lead-meta .label {
        font-size: 9pt;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #D7712A;
        font-weight: 600;
        margin-bottom: 0.2cm;
    }
    .cover-lead-meta .smiles {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 9.5pt;
        color: #1e293b;
        word-break: break-all;
        line-height: 1.4;
        padding: 0.4cm 0.6cm;
        background: #f8fafc;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.6cm;
    }
    .cover-stats {
        display: flex;
        gap: 1.5cm;
        margin-top: 0.6cm;
    }
    .cover-stat {
        flex: 1;
    }
    .cover-stat .val {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 22pt;
        font-weight: 500;
        color: #1e293b;
        line-height: 1;
    }
    .cover-stat .key {
        font-size: 8pt;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #64748b;
        margin-top: 0.15cm;
    }
    .cover-footer {
        position: relative; z-index: 2;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 9pt;
        color: #64748b;
        border-top: 1px solid #e2e8f0;
        padding-top: 0.6cm;
    }

    /* ── Inner-page chrome ──────────────────────────────────────────── */
    .page-section { page-break-before: always; padding-top: 0.5cm; }
    .page-section:first-of-type { page-break-before: auto; }

    h2 {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 18pt;
        font-weight: 500;
        color: #1e293b;
        margin: 0 0 0.4cm 0;
        padding-bottom: 0.3cm;
        border-bottom: 2px solid #D7712A;
    }
    h3 {
        font-family: 'Fraunces', Georgia, serif;
        font-size: 13pt;
        font-weight: 500;
        color: #1e293b;
        margin-top: 0.7cm;
        margin-bottom: 0.3cm;
    }
    .narrative {
        column-count: 2;
        column-gap: 1cm;
        column-rule: 1px solid #f1f5f9;
        text-align: justify;
        font-size: 9.5pt;
        line-height: 1.6;
        color: #334155;
    }
    .narrative p { margin: 0 0 0.5cm 0; }

    /* ── Lead-compound dossier card (page 2) ────────────────────────── */
    .hero-box {
        display: grid;
        grid-template-columns: 9cm 1fr;
        gap: 1cm;
        background: #fafafa;
        border-radius: 14px;
        padding: 1cm;
        margin-bottom: 0.8cm;
        border: 1px solid #e2e8f0;
    }
    .hero-img {
        width: 100%; height: 9cm;
        background: white;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        padding: 0.5cm;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .hero-img img { width: 100%; height: 100%; object-fit: contain; }
    .admet-tag {
        display: inline-block;
        padding: 0.18cm 0.4cm;
        border-radius: 999px;
        font-size: 8.5pt;
        font-weight: 500;
        margin-right: 0.2cm;
        margin-bottom: 0.2cm;
    }
    .tag-liability { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    .tag-strength { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .tag-neutral { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

    /* ── Per-analog trading cards (2-up in landscape) ───────────────── */
    .analog-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.6cm;
        margin-top: 0.4cm;
    }
    .analog-card {
        display: grid;
        grid-template-columns: 11cm 1fr;
        gap: 0.6cm;
        background: white;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 0.6cm;
        /* WeasyPrint debug fix (2026-06-10): page-break-inside: avoid on
           .analog-card was THE assert-not-page-empty trigger. Verified by
           bisect against report_38412455.html, removing this one rule
           makes WeasyPrint succeed (869KB styled PDF) while keeping every
           other style intact. Reason: a card with min-height: 9cm +
           page-break-inside: avoid + embedded base64 image enters a
           "won't-fit → push to new page → empty page" loop when the
           previous card consumed most of the current page. The trade-off
           is that some cards may split across a page boundary, acceptable
           given the alternative is xhtml2pdf's broken layout. */
        position: relative;
        min-height: 9cm;
        max-height: 13cm;
    }
    .analog-rank {
        position: absolute;
        top: 0.5cm; right: 0.6cm;
        font-family: 'Fraunces', Georgia, serif;
        font-size: 28pt;
        font-weight: 400;
        color: #D7712A;
        line-height: 1;
        opacity: 0.9;
    }
    .analog-struct {
        background: #fafafa;
        border-radius: 8px;
        border: 1px solid #f1f5f9;
        padding: 0.3cm;
        display: flex;
        flex-direction: column;
    }
    .analog-struct img { width: 100%; max-height: 8cm; object-fit: contain; }
    .analog-struct .smiles {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 6.5pt;
        color: #64748b;
        word-break: break-all;
        margin-top: 0.2cm;
        line-height: 1.3;
    }
    .analog-meta {
        font-size: 8.5pt;
        color: #1e293b;
    }
    .analog-meta .row { margin-bottom: 0.18cm; line-height: 1.4; }
    .analog-meta .row .lbl {
        display: inline-block;
        min-width: 2.2cm;
        text-transform: uppercase;
        font-size: 7.5pt;
        letter-spacing: 0.06em;
        color: #94a3b8;
        font-weight: 600;
    }
    .analog-mods {
        margin-top: 0.25cm;
        padding: 0.25cm 0.4cm;
        background: #fff8f1;
        border-left: 2px solid #D7712A;
        border-radius: 4px;
        font-size: 8pt;
        line-height: 1.35;
        color: #475569;
    }
    .delta-chip {
        display: inline-block;
        padding: 0.1cm 0.3cm;
        border-radius: 4px;
        font-size: 7.5pt;
        margin: 0.05cm 0.15cm 0.05cm 0;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
    }
    .delta-up { background: #dcfce7; color: #166534; }
    .delta-down { background: #fee2e2; color: #991b1b; }
    .delta-flat { background: #f1f5f9; color: #475569; }

    /* ── Data tables ────────────────────────────────────────────────── */
    .data-grid { width: 100%; border-collapse: collapse; margin-top: 0.4cm; }
    .data-grid th {
        background: #1e293b; color: white;
        padding: 0.3cm; font-size: 8.5pt; font-weight: 600;
        text-align: left;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .data-grid td {
        padding: 0.3cm; border-bottom: 1px solid #f1f5f9;
        font-size: 8.5pt; vertical-align: top;
    }
    .data-grid tr:nth-child(even) td { background: #fafafa; }
    .mol-img { width: 3cm; background: white; border: 1px solid #e2e8f0; border-radius: 4px; padding: 0.1cm; }
    .score-badge { font-weight: 600; color: #D7712A; font-family: 'JetBrains Mono', monospace; font-size: 9.5pt; }
    .change-positive { color: #166534; font-weight: 600; }
    .change-negative { color: #991b1b; font-weight: 600; }
    .change-neutral { color: #475569; }

    .appendix-table { width: 100%; border-collapse: collapse; font-size: 8pt; }
    .appendix-table th { background: #334155; color: white; padding: 0.2cm; font-size: 8pt; text-align: left; }
    .appendix-table td { padding: 0.2cm; border-bottom: 1px solid #e2e8f0; font-size: 8pt; }

    .citation {
        font-size: 8.5pt; color: #475569;
        margin: 0.15cm 0; padding-left: 0.4cm;
        border-left: 2px solid #D7712A;
    }
    .citation-title { font-weight: 600; color: #1e293b; }
    .citation-meta { color: #64748b; font-style: italic; }

    .info-card {
        background: #fafafa;
        border-radius: 10px;
        padding: 0.6cm;
        margin: 0.4cm 0;
        border: 1px solid #e2e8f0;
        font-size: 9pt;
        color: #475569;
        line-height: 1.55;
    }
    .info-card strong { color: #1e293b; }
    """
    
    # Format narrative into paragraphs (split on double newlines)
    narrative_html = "".join(
        f"<p>{p.strip()}</p>" for p in narrative.split("\n\n") if p.strip()
    ) if narrative else ""

    # Lead-compound preview SMILES (truncated for cover display)
    lead_smiles_display = lead_smiles if len(lead_smiles) <= 120 else lead_smiles[:117] + "..."

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>{css_template}</style>
    </head>
    <body>

        <!-- ───────────────────────── COVER PAGE ───────────────────────── -->
        <div class="cover">
            <div class="cover-band"></div>

            <div class="cover-brand">Benchside · Autonomous Lead Optimizer</div>

            <div class="cover-title">
                <h1>Lead Optimization<br/>Report</h1>
                <div class="subtitle">
                    A computational dossier of structural analogs ranked by a multi-objective
                    Pareto strategy, with ADMET deltas, synthetic accessibility, and
                    medicinal-chemistry rationale.
                </div>
            </div>

            <div class="cover-lead">
                <div class="cover-lead-img">
                    <img src="data:image/png;base64,{lead_img}" alt="Lead compound" />
                </div>
                <div class="cover-lead-meta">
                    <div class="label">Lead Compound</div>
                    <div class="smiles">{lead_smiles_display}</div>
                    <div class="cover-stats">
                        <div class="cover-stat">
                            <div class="val">{len(top_analogs)}</div>
                            <div class="key">Analogs Ranked</div>
                        </div>
                        <div class="cover-stat">
                            <div class="val">{search_space_size:,}</div>
                            <div class="key">Search Space</div>
                        </div>
                        <div class="cover-stat">
                            <div class="val">{len(lead_profile.liabilities)}</div>
                            <div class="key">Target Liabilities</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="cover-footer">
                <span>Generated {generated_date}</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 8pt; color: #94a3b8;">Task · {task_id}</span>
            </div>
        </div>

        <!-- ───────────────────── LEAD-COMPOUND DOSSIER ───────────────────── -->
        <div class="page-section">
            <h2>Lead Compound Dossier</h2>

            <div class="hero-box">
                <div class="hero-img">
                    <img src="data:image/png;base64,{lead_img}" alt="Lead structure" />
                </div>
                <div>
                    <h3 style="margin-top: 0;">Profile Summary</h3>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 8pt; color: #475569; word-break: break-all; padding: 0.3cm; background: #f8fafc; border-radius: 6px; margin-bottom: 0.5cm;">{lead_smiles}</div>

                    <h4 style="color: #991b1b; margin: 0.3cm 0 0.2cm 0; font-size: 10pt;">Target Liabilities</h4>
                    <div>{" ".join([f'<span class="admet-tag tag-liability">{l.endpoint}: {l.value:.2f} ({l.direction})</span>' for l in lead_profile.liabilities])}</div>

                    <h4 style="color: #166534; margin: 0.4cm 0 0.2cm 0; font-size: 10pt;">Strengths to Maintain</h4>
                    <div>{" ".join([f'<span class="admet-tag tag-strength">{s}</span>' for s in lead_profile.strengths])}</div>

                    {_syba_block(lead_syba_score, lead_sa_score)}
                </div>
            </div>

            <h3>Design Strategy Narrative</h3>
            <div class="narrative">{narrative_html}</div>
        </div>

        <!-- ─────────────────── OPTIMIZATION METHODOLOGY ─────────────────── -->
        <div class="page-section">
            <h2>Optimization Methodology</h2>

            <div class="info-card">
                <h3 style="margin-top: 0;">Campaign Configuration</h3>
                <p>
                    <strong>Ligand Interaction Diagram (LID):</strong> {"Used" if used_lid else "Not provided"}<br/>
                    <strong>Search Space Size:</strong> {search_space_size:,} combinations tested<br/>
                    <strong>Total Strategies:</strong> {len(top_analogs) if top_analogs else 0} primary + {len(secondary_targets) if secondary_targets else 0} secondary
                </p>

                {f'''
                <h3>Secondary Targets (Unlocked Restricted Groups)</h3>
                <p>The following restricted groups were unlocked for conservative modification due to weak binding interactions:</p>
                <ul>
                    {''.join([f'<li><strong>{t["group_name"]}</strong>, {t["reason"]}</li>' for t in secondary_targets])}
                </ul>
                ''' if secondary_targets else ''}

                {f'''
                <h3>No-LID Mode</h3>
                <p>No LID was provided. All detected functional groups were treated as modifiable targets.
                The search space was expanded to {search_space_size:,} combinations to ensure comprehensive exploration.</p>
                ''' if not used_lid else ''}

                <h3>Process Notes</h3>
                <p>{methodology_notes or "Standard pipeline configuration was applied."}</p>
            </div>
        </div>
    """
    
    # ─────────────────── SUPPORTING LITERATURE (page section) ───────────────────
    if pubmed_citations:
        html_content += """
        <div class="page-section">
            <h2>Supporting Literature</h2>
            <p style="color: #64748b; margin-bottom: 0.4cm;">
                Publications providing evidence for the structural transformations employed in this campaign.
            </p>
        """
        for mod, articles in pubmed_citations.items():
            if articles:
                html_content += f'<div style="margin-bottom: 0.5cm;"><h3 style="margin-bottom: 0.25cm;">{mod}</h3>'
                for art in articles:
                    html_content += f"""
                    <div class="citation">
                        <div class="citation-title">{art.get('title', 'N/A')}</div>
                        <div class="citation-meta">{art.get('authors', 'N/A')} ({art.get('year', 'N/A')}) · {art.get('journal', 'N/A')}</div>
                    </div>
                    """
                html_content += '</div>'
        html_content += "</div>"

    # ─────────────────── TOP-10 TRADING CARDS (elite section) ───────────────────
    # Two cards per landscape page, structure on left, properties on right.
    html_content += """
        <div class="page-section">
            <h2>Top 10 Candidates, Trading Cards</h2>
            <p style="color: #64748b; margin-bottom: 0.4cm;">
                Elite analogs ranked by Pareto score. Each card shows the structural
                modification, ADMET deltas versus the lead, and a synthetic-accessibility
                readout. <span style="color:#166534;font-weight:600;">Green</span> deltas
                indicate improvement; <span style="color:#991b1b;font-weight:600;">red</span> indicates degradation.
            </p>
            <div class="analog-grid">
    """

    for i, a in enumerate(top_analogs[:10]):
        changes = a.get('changes', {})
        # Build delta chips
        delta_chips = []
        for c in changes.get('liabilities', []):
            css = 'delta-up' if c['improved'] else 'delta-down'
            sign = '↓' if c['improved'] else '↑'
            delta_chips.append(f'<span class="delta-chip {css}">{c["endpoint"]} {sign} {abs(c["pct"]):.0f}%</span>')
        for c in changes.get('strengths', []):
            css = 'delta-up' if c['improved'] else 'delta-down'
            sign = '↑' if c['improved'] else '↓'
            delta_chips.append(f'<span class="delta-chip {css}">{c["endpoint"]} {sign} {abs(c["pct"]):.0f}%</span>')

        admet = a.get("admet_results", {})
        # Audit 2026-06-09: was reading "gasa_score" (an int aliased at the
        # top level), not "GASA" (the dict). That made every analog show ","
        # for synth. Now reads the GASA dict, with the top-level syba_score
        # as a fallback for analogs persisted before the field rename.
        gasa = admet.get("GASA") or admet.get("gasa_score") or {}
        if not isinstance(gasa, dict):
            gasa = {}
        if not gasa.get("syba_score") and a.get("syba_score") is not None:
            gasa = {**gasa, "syba_score": a.get("syba_score"), "sa_score": a.get("sa_score")}
        sa_display = _syba_short(gasa, fallback=",")

        mods_html = "; ".join(a.get('modifications', [])) or ","
        smiles_short = a['smiles'] if len(a['smiles']) <= 90 else a['smiles'][:87] + "..."

        html_content += f"""
            <div class="analog-card">
                <div class="analog-rank">{i+1:02d}</div>
                <div class="analog-struct">
                    <img src="data:image/png;base64,{a.get('img_base64', '')}" alt="Analog {i+1}" />
                    <div class="smiles">{smiles_short}</div>
                </div>
                <div class="analog-meta">
                    <div class="row"><span class="lbl">Pareto</span> <span class="score-badge">{a.get('pareto_score', 0.0):.4f}</span></div>
                    <div class="row"><span class="lbl">Synth</span> {sa_display}</div>
                    <div class="row"><span class="lbl">Deltas</span></div>
                    <div style="margin-top:0.1cm;">{"".join(delta_chips[:8]) or '<span style="color:#94a3b8;font-style:italic;">no significant deltas</span>'}</div>
                    <div class="analog-mods"><strong>Modification:</strong> {mods_html}</div>
                </div>
            </div>
        """

    html_content += """
            </div>
        </div>
    """

    # ─────────────────── COMPARATIVE TABLE, ranks 1-50 ───────────────────
    html_content += """
        <div class="page-section">
            <h2>Comparative Candidate Table</h2>
            <p style="color: #64748b; margin-bottom: 0.4cm;">
                Side-by-side ADMET deltas for the top 50 analogs. Use this table to compare
                multiple candidates at a glance before drilling into the trading cards above.
            </p>
            <table class="data-grid">
                <thead>
                    <tr>
                        <th style="width: 0.8cm;">#</th>
                        <th style="width: 3.2cm;">Structure</th>
                        <th style="width: 5.2cm;">ADMET Δ vs Lead</th>
                        <th>Modifications</th>
                        <th style="width: 1.8cm;">Synth</th>
                        <th style="width: 1.8cm;">Score</th>
                    </tr>
                </thead>
                <tbody>
    """

    for i, a in enumerate(top_analogs[:50]):
        changes = a.get('changes', {})
        change_items = []
        for c in changes.get('liabilities', []):
            delta_str = f"{c['delta']:+.2f}"
            pct_str = f" ({c['pct']:+.0f}%)" if c['pct'] != 0 else ""
            css_class = 'change-positive' if c['improved'] else 'change-negative'
            change_items.append(f'<span class="{css_class}">{c["endpoint"]}: {delta_str}{pct_str}</span>')
        for c in changes.get('strengths', []):
            delta_str = f"{c['delta']:+.2f}"
            pct_str = f" ({c['pct']:+.0f}%)" if c['pct'] != 0 else ""
            css_class = 'change-positive' if c['improved'] else 'change-negative'
            change_items.append(f'<span class="{css_class}">{c["endpoint"]}: {delta_str}{pct_str}</span>')

        admet = a.get("admet_results", {})
        # Audit 2026-06-09: was reading "gasa_score" (an int aliased at the
        # top level), not "GASA" (the dict). That made every analog show ","
        # for synth. Now reads the GASA dict, with the top-level syba_score
        # as a fallback for analogs persisted before the field rename.
        gasa = admet.get("GASA") or admet.get("gasa_score") or {}
        if not isinstance(gasa, dict):
            gasa = {}
        if not gasa.get("syba_score") and a.get("syba_score") is not None:
            gasa = {**gasa, "syba_score": a.get("syba_score"), "sa_score": a.get("sa_score")}
        sa_display = _syba_short(gasa, fallback=",")

        html_content += f"""
                <tr>
                    <td>{i+1}</td>
                    <td><img src="data:image/png;base64,{a.get('img_base64', '')}" class="mol-img" /></td>
                    <td style="font-size: 7.5pt; line-height: 1.5;">
                        {"<br>".join(change_items[:6])}
                    </td>
                    <td style="font-size: 8pt;">{"<br>".join(a.get('modifications', []))}</td>
                    <td style="text-align: center;">{sa_display}</td>
                    <td class="score-badge">{a.get('pareto_score', 0.0):.4f}</td>
                </tr>
        """

    html_content += """
                </tbody>
            </table>
        </div>
    """
    
    # ─────────────────── APPENDIX, Ranks 51+ ───────────────────
    if len(top_analogs) > 50:
        html_content += f"""
        <div class="page-section">
            <h2>Appendix, Additional Candidates (Rank 51–{len(top_analogs)})</h2>
            <p style="color: #64748b; margin-bottom: 0.4cm;">
                Summary table of additional analogs ranked beyond the top 50.
                Full structural data is available in the attached SDF library.
            </p>
            <table class="appendix-table">
                <thead>
                    <tr>
                        <th style="width: 1cm;">Rank</th>
                        <th>SMILES</th>
                        <th style="width: 6cm;">Modifications</th>
                        <th style="width: 2cm;">Pareto Score</th>
                    </tr>
                </thead>
                <tbody>
        """

        for i, a in enumerate(top_analogs[50:], start=51):
            html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td style="font-family: 'JetBrains Mono', monospace; font-size: 7pt; word-break: break-all;">{a['smiles']}</td>
                        <td style="font-size: 7.5pt;">{'; '.join(a.get('modifications', []))}</td>
                        <td style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #D7712A;">{a.get('pareto_score', 0.0):.4f}</td>
                    </tr>
            """

        html_content += """
                </tbody>
            </table>
        </div>
        """

    # ─────────────────── COMPUTATIONAL METHODOLOGY ───────────────────
    html_content += """
        <div class="page-section">
            <h2>Computational Methodology</h2>
            <div class="info-card">
                <p><strong>Structural Transformations:</strong> Bioisosteric replacement strategies were selected
                from a curated database of 479 RDKit-validated transformations across 22 categories
                (aromatic-ring swaps, amine modifications, carboxylic-acid bioisosteres, CNS penetration,
                nitrogen-heterocycle swaps, polarity adjustments, halogen substitutions, steric shielding,
                metabolic stability, etc.), derived from medicinal chemistry literature including Brown
                (<em>Bioisosteres in Medicinal Chemistry</em>) and Wilson &amp; Gisvold.</p>

                <p><strong>Synthetic Accessibility:</strong> Reported as the SYBA classifier score
                (Vor&scaron;il&aacute;k et al., <em>J. Cheminform.</em> 2020, 12:35), a naive Bayes classifier
                over ECFP4 fragments, AUC &gt; 0.81, where the signed score is positive for synthesizable molecules
                and negative for hard-to-make molecules. SYBA outperforms the legacy Ertl SAScore (AUC ~0.79)
                on standard benchmarks. Ertl SAScore is still computed internally as a cross-check and persisted
                in the audit log, but is not surfaced in this report.</p>

                <p><strong>ADMET Predictions:</strong> Generated via ADMET-AI (Chemprop v2) graph neural-network
                ensemble trained on 46 absorption, distribution, metabolism, excretion, and toxicity endpoints
                with DrugBank percentile benchmarking.</p>

                <p><strong>Multi-Objective Optimization:</strong> Context-aware Pareto ranking with Butina
                clustering for chemical diversity. Weights are determined by therapeutic-context analysis at
                runtime, biased toward the lead compound's documented liabilities.</p>

                <p>Full technical data including all ADMET predictions and molecular descriptors are included
                in the attached SDF discovery library.</p>
            </div>
        </div>

    </body>
    </html>
    """
    
    # Save files
    html_path = report_dir / f"{task_id}.html"
    pdf_path = report_dir / f"{task_id}.pdf"
    sdf_path = report_dir / f"{task_id}.sdf"
    
    with open(html_path, "w") as f:
        f.write(html_content)

    # Robust fallback chain. WeasyPrint is the primary because it
    # handles modern CSS (grid, @page rules, custom fonts, gradients)
    # required by the elite landscape design. xhtml2pdf is a backup
    # that's been around longer and copes with simpler markup.
    # If both fail we fall back to a minimal text-only PDF so the
    # user gets *something* rather than a None they can't download.
    pdf_generated = False
    pdf_errors: list[str] = []

    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(str(pdf_path))
        logger.info(f"✅ PDF generated via WeasyPrint: {pdf_path}")
        pdf_generated = True
    except Exception as e:
        # Log type + repr so silent AssertionError (no message) still surfaces.
        import traceback as _tb
        err_repr = f"{type(e).__name__}: {e!r}"
        pdf_errors.append(f"WeasyPrint: {err_repr}")
        logger.warning(
            f"⚠️ WeasyPrint failed, trying xhtml2pdf fallback: {err_repr}\n"
            f"{_tb.format_exc()}"
        )

    if not pdf_generated:
        try:
            from xhtml2pdf import pisa
            with open(str(pdf_path), "wb") as out:
                status = pisa.CreatePDF(html_content, dest=out)
            if status.err:
                raise RuntimeError(f"xhtml2pdf reported {status.err} errors")
            logger.info(f"✅ PDF generated via xhtml2pdf fallback: {pdf_path}")
            pdf_generated = True
        except Exception as e:
            pdf_errors.append(f"xhtml2pdf: {e}")
            logger.warning(f"⚠️ xhtml2pdf also failed, falling back to text PDF: {e}")

    if not pdf_generated:
        # Last-ditch: render a minimal text-only PDF using reportlab so
        # the user gets a downloadable file rather than a 404.
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import landscape, A4
            c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
            c.setFont("Helvetica-Bold", 18)
            c.drawString(72, 540, "Lead Optimization Report")
            c.setFont("Helvetica", 10)
            c.drawString(72, 510, f"Task: {task_id}")
            c.drawString(72, 495, f"Lead SMILES: {lead_smiles[:120]}")
            c.drawString(72, 470, f"Analogs ranked: {len(top_analogs)}")
            c.drawString(72, 455, f"Search space: {search_space_size:,} combinations")
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColorRGB(0.6, 0.3, 0.1)
            c.drawString(72, 420, "Rich PDF rendering failed for this report. The HTML version and SDF library are still attached.")
            c.setFont("Helvetica", 8)
            y = 390
            for i, a in enumerate(top_analogs[:30]):
                if y < 50:
                    c.showPage(); y = 540
                c.drawString(72, y, f"#{i+1:02d}  score={a.get('pareto_score', 0.0):.4f}  {a['smiles'][:90]}")
                y -= 12
            c.save()
            logger.info(f"✅ PDF generated via reportlab text fallback: {pdf_path}")
            pdf_generated = True
        except Exception as e:
            pdf_errors.append(f"reportlab: {e}")

    if not pdf_generated:
        logger.error(f"❌ All PDF backends failed: {' | '.join(pdf_errors)}")
        pdf_path = None
    
    _generate_sdf(top_analogs, str(sdf_path), lead_smiles)
    
    return {"html": str(html_path), "pdf": str(pdf_path), "sdf": str(sdf_path)}
