
import asyncio
import logging
from uuid import UUID
from app.services.embeddings import embeddings_service
from app.core.database import db as db_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

MEDCHEM_COLLECTION_ID = UUID("a1b2c3d4-0000-0000-0000-000000000001")
MEDCHEM_USER_ID = UUID("a1b2c3d4-0000-0000-0000-000000000002")

SEED_KNOWLEDGE = [
    {
        "category": "admet_strategy",
        "title": "Improving Oral Bioavailability",
        "content": """To improve oral bioavailability:
- Reduce TPSA below 140 Å² for better membrane permeability.
- Maintain LogP between 1-3 for optimal balance between solubility and permeability.
- Reduce H-bond donors to ≤3 to minimize desolvation energy penalties.
- Introduce N-methylation on exposed amides to reduce H-bond donor count.
- Replace hydroxyl groups with fluorine to reduce first-pass metabolic clearance."""
    },
    {
        "category": "toxicology",
        "title": "Reducing hERG Liability",
        "content": """Strategies to reduce hERG channel inhibition:
- Remove or mask basic nitrogen centers (pKa > 7) that interact with the hERG pore.
- Replace tertiary amines with non-basic alternatives like amides, sulfonamides, or ureas.
- Reduce overall lipophilicity (LogP < 3.5) to decrease hydrophobic trapping.
- Add polar groups (e.g., hydroxyl, sulfone) to reduce affinity for the hydrophobic channel.
- Shorten or rigidify flexible alkyl chains connecting basic centers to aromatic rings."""
    },
    {
        "category": "admet_strategy",
        "title": "Improving Metabolic Stability",
        "content": """Methods to block metabolic soft spots:
- Block metabolically labile positions (especially para-phenyl) with fluorine or small alkyl groups.
- Replace ester groups (labile to esterases) with amides, reverse amides, or oxadiazoles.
- Replace phenyl groups with pyridine or other electron-deficient heterocycles to block oxidative metabolism.
- Introduce gem-dimethyl groups adjacent to metabolic sites (steric hindrance).
- Replace N-methyl with cyclopropyl or other groups that resist N-dealkylation."""
    },
    {
        "category": "admet_strategy",
        "title": "Improving BBB Penetration",
        "content": """Design rules for CNS-active compounds:
- Reduce Molecular Weight (MW) below 450 Da.
- Maintain TPSA below 90 Å² (ideally < 60-70 Å²).
- Remove carboxylic acid groups (use tetrazole, oxadiazole, or sulfonamide as bioisosteres).
- Reduce H-bond donors to ≤2.
- LogP should be in the range of 1.5 to 4.0 for passive diffusion."""
    },
    {
        "category": "structural_alert",
        "title": "Reactive Functional Groups",
        "content": """Groups flagged as Michael acceptors or reactive electrophiles:
- α,β-unsaturated carbonyls (aldehydes, ketones, esters).
- Acyl halides (R-C(=O)-X).
- Epoxides and aziridines (strained three-membered rings).
- Alkyl halides (R-CH2-X, especially benzylic/allylic).
- Isocyanates and isothiocyanates."""
    },
    {
        "category": "toxicology",
        "title": "Structural Alerts for Mutagenicity",
        "content": """Common structural alerts for mutagenicity (Ames test):
- Aromatic amines (anilines): Risk of N-hydroxylation to reactive nitrenium ions.
- Nitroarenes: Reductive metabolism to reactive hydroxylamines.
- Hydrazines (R-NH-NH2): Potential for DNA alkylation and hepatotoxicity.
- Thiophenes: Risk of oxidative ring-opening to reactive S-oxides or epoxides.
- Quinones: Capable of redox cycling and generating oxidative stress."""
    },
    {
        "category": "bioisostere",
        "title": "Carboxylic Acid Bioisosteres",
        "content": """Classical and non-classical replacements for -COOH:
- Tetrazole: Similar pKa (~4.5-5.0), larger volume, better lipophilicity/BBB penetration.
- 1,2,4-Oxadiazol-5(4H)-one: Bioisosteric with similar acidity.
- Acyl-sulfonamides (-CONHSO2R): Tunable pKa, additional vector for interaction.
- Squaric acid derivatives: Planar, acidic, capable of complex H-bonding."""
    }
]

async def seed_medchem_knowledge():
    """Seed the database with high-quality MedChem rules."""
    logger.info("🌱 Seeding MedChem Knowledge Bootstrap...")
    
    db = db_manager.get_client()
    texts = [f"Title: {k['title']}\n\n{k['content']}" for k in SEED_KNOWLEDGE]
    
    logger.info(f"🧠 Generating embeddings for {len(texts)} seed entries...")
    embeddings = await embeddings_service.generate_embeddings_batch(texts)
    
    bulk_data = []
    expected_dims = settings.EMBEDDING_DIMENSIONS
    
    for i, entry in enumerate(SEED_KNOWLEDGE):
        emb = embeddings[i]
        if emb and len(emb) == expected_dims:
            bulk_data.append({
                "conversation_id": str(MEDCHEM_COLLECTION_ID),
                "user_id": str(MEDCHEM_USER_ID),
                "content": texts[i],
                "embedding": emb,
                "metadata": {
                    "source_type": "medchem_seed",
                    "category": entry["category"],
                    "title": entry["title"],
                    "source": "Benchside Seed Knowledge"
                }
            })
    
    if bulk_data:
        logger.info(f"💾 Inserting {len(bulk_data)} seed entries...")
        result = db.table("document_chunks").insert(bulk_data).execute()
        if result.data:
            logger.info(f"✅ Successfully seeded {len(result.data)} MedChem entries.")
            return True
    
    return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_medchem_knowledge())
