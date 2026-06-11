import asyncio
import base64
import logging
import os
from typing import Optional
from app.core.container import container
from .orchestrator import run_lead_optimization
from .schemas import VisionAgentOutput, FunctionalGroupInteraction, ExposedGroup

logger = logging.getLogger(__name__)


def base64_to_bytes(b64_string: str) -> bytes:
    """Decode a base64-encoded string to raw bytes."""
    if ',' in b64_string:
        b64_string = b64_string.split(',', 1)[1]
    return base64.b64decode(b64_string)


def _build_vision_output_from_metadata(metadata: dict) -> Optional[VisionAgentOutput]:
    """
    Reconstruct VisionAgentOutput from reviewed groups stored in metadata.
    Used when resuming a task after user review.
    """
    if not metadata:
        return None

    reviewed_restricted = metadata.get("reviewed_restricted_groups")
    reviewed_target = metadata.get("reviewed_target_groups")

    if not reviewed_restricted and not reviewed_target:
        return None

    restricted = []
    for g in reviewed_restricted or []:
        # Accept either {residues: [...]} (new) or {residue: "..."} (legacy).
        # The schema's model_validator backfills the missing direction.
        restricted.append(FunctionalGroupInteraction(
            group_name=g.get("group_name", ""),
            residue=g.get("residue") or None,
            residues=g.get("residues") or [],
            interaction_type=g.get("interaction_type", "hydrophobic"),
            interaction_types=g.get("interaction_types") or [],
            confidence=g.get("confidence", 0.5),
            atom_indices=g.get("atom_indices") or [],
        ))

    target = []
    for g in reviewed_target or []:
        target.append(ExposedGroup(
            group_name=g.get("group_name", ""),
            position_description=g.get("position_description", ""),
            atom_indices=g.get("atom_indices") or [],
        ))

    reviewed_structural_core = metadata.get("reviewed_structural_core_groups") or []
    structural_core = []
    for g in reviewed_structural_core:
        structural_core.append(ExposedGroup(
            group_name=g.get("group_name", ""),
            position_description=g.get("position_description", ""),
            atom_indices=g.get("atom_indices") or [],
        ))

    return VisionAgentOutput(
        restricted_groups=restricted,
        structural_core_groups=structural_core,
        target_groups=target,
        overall_confidence=0.85,
        scaffold_atoms=metadata.get("reviewed_scaffold_atoms") or [],
    )


async def lead_optimizer_worker():
    """
    Background worker that processes optimization tasks one by one.
    Ensures sequential processing and respects API rate limits.
    """
    logger.info("🚀 Lead Optimizer Worker started")
    db = container.get_db()

    # Per-user round-robin state: tracks the timestamp at which each
    # user_id last had a task picked. Users whose last pick was longer
    # ago (or who have never had one this process lifetime) go first.
    # This is in-memory only, if the worker restarts the state resets
    # and tie-breaks fall back to FIFO, which is acceptable.
    import time as _time
    last_picked_at: dict = {}

    while True:
        try:
            # Fetch ALL pending/running tasks (typical queue depth is
            # tens at most, Supabase returns this fast). We then pick
            # in-process for fair scheduling.
            result = db.table("optimization_tasks") \
                .select("*") \
                .in_("status", ["pending", "running"]) \
                .order("created_at") \
                .limit(200) \
                .execute()

            if not result.data:
                await asyncio.sleep(10)
                continue

            # Per-user fair-share scheduling: group by user_id, pick the
            # user who has been waiting longest (lowest last_picked_at
            # value, or never picked this lifetime), then pop that user's
            # OLDEST pending/running task. Effect: round-robin across
            # users, FIFO within each user. A power user submitting 10
            # back-to-back tasks no longer monopolises the queue.
            #
            # Skip tasks awaiting user review when picking the candidate ,
            # those don't advance and would starve other users.
            candidates_by_user: dict = {}
            for row in result.data:
                rmeta = row.get("metadata") or {}
                if rmeta.get("awaiting_review"):
                    continue
                uid = row.get("user_id")
                if uid not in candidates_by_user:
                    candidates_by_user[uid] = row  # sorted by created_at already; first per user is oldest

            if not candidates_by_user:
                # Every queued task is awaiting review. Idle.
                await asyncio.sleep(5)
                continue

            # Pick the user with the smallest last_picked_at value
            # (default 0 = never picked this lifetime → goes first).
            chosen_user = min(
                candidates_by_user.keys(),
                key=lambda u: last_picked_at.get(u, 0.0),
            )
            task = candidates_by_user[chosen_user]
            last_picked_at[chosen_user] = _time.time()

            task_id = task["id"]
            status = task["status"]
            metadata = task.get("metadata", {}) or {}

            logger.info(f"🔄 Processing task {task_id} (status: {status})")

            # Update status to processing
            db.table("optimization_tasks").update({
                "status": "processing",
                "started_at": "now()"
            }).eq("id", task_id).execute()

            # Build vision output from reviewed groups if available
            vision_output = None
            if status == "running" and metadata.get("reviewed_restricted_groups"):
                vision_output = _build_vision_output_from_metadata(metadata)
                if vision_output:
                    logger.info(f"Task {task_id}: resuming with reviewed vision output")

            # Progress callback to update DB
            async def progress(stage, percent, details):
                try:
                    db.table("optimization_tasks").update({
                        "current_stage": stage,
                        "progress": percent,
                        "stage_details": details
                    }).eq("id", task_id).execute()
                except Exception as e:
                    logger.error(f"Progress update failed: {e}")

            try:
                # Execute pipeline.
                # Pass task_id so the orchestrator scopes _DEAD_SMIRKS_BY_TASK per task
                # (Batch-1 refactor). The orchestrator's pause-for-review guard is already
                # short-circuited by passing vision_output=<rebuilt>, so re-passing task_id
                # here does NOT cause a re-pause.
                result_data = await run_lead_optimization(
                    lead_smiles=task["lead_smiles"],
                    lid_diagram=base64_to_bytes(task["lid_diagram_base64"]),
                    user_context=task.get("user_context", ""),
                    visual_hints=task.get("visual_hints", ""),
                    progress_callback=progress,
                    task_id=task_id,
                    vision_output=vision_output
                )

                if result_data is None:
                    # Pipeline paused for review, status already updated by orchestrator
                    logger.info(f"Task {task_id}: paused for vision review")
                    continue

                # Pipeline completed successfully
                db.table("optimization_tasks").update({
                    "status": "completed",
                    "progress": 100,
                    "current_stage": "report",
                    "stage_details": "Optimization complete",
                    "result": result_data.dict(),
                    "pdf_path": result_data.report_pdf_path,
                    "sdf_path": result_data.sdf_path,
                    "total_analogs": result_data.total_analogs_generated,
                    "total_passed": result_data.total_passed_prefilter,
                    "completed_at": "now()"
                }).eq("id", task_id).execute()

                logger.info(f"✅ Task {task_id} completed successfully")

                # Email notification.
                # The user table is `users` in this Supabase schema, not `profiles` ,
                # research_tasks.py confirmed the working pattern. Previous lookup raised
                # PGRST205 "Could not find the table 'public.profiles'" and silently swallowed
                # every lead-optimizer completion email.
                try:
                    from app.services.email import EmailService
                    email_service = EmailService()
                    user_res = db.table("users").select("email").eq("id", task["user_id"]).single().execute()
                    if user_res.data and user_res.data.get("email"):
                        pdf_bytes = None
                        sdf_bytes = None
                        
                        if result_data.report_pdf_path and os.path.exists(result_data.report_pdf_path):
                            with open(result_data.report_pdf_path, "rb") as f:
                                pdf_bytes = f.read()
                        
                        if result_data.sdf_path and os.path.exists(result_data.sdf_path):
                            with open(result_data.sdf_path, "rb") as f:
                                sdf_bytes = f.read()
                        
                        await email_service.send_optimization_email(
                            to_email=user_res.data["email"],
                            task_id=task_id,
                            lead_smiles=task["lead_smiles"],
                            status="completed",
                            pdf_bytes=pdf_bytes,
                            sdf_bytes=sdf_bytes
                        )
                except Exception as email_err:
                    logger.error(f"Failed to send completion email: {email_err}")

            except Exception as e:
                logger.error(f"❌ Task {task_id} failed: {e}")
                db.table("optimization_tasks").update({
                    "status": "failed",
                    "error": str(e),
                    "stage_details": f"Pipeline error: {str(e)}"
                }).eq("id", task_id).execute()
                
                # Send failure email
                try:
                    from app.services.email import EmailService
                    email_service = EmailService()
                    user_res = db.table("profiles").select("email").eq("id", task["user_id"]).single().execute()
                    if user_res.data and user_res.data.get("email"):
                        await email_service.send_optimization_email(
                            to_email=user_res.data["email"],
                            task_id=task_id,
                            lead_smiles=task["lead_smiles"],
                            status="failed",
                            error=str(e)
                        )
                except Exception as email_err:
                    logger.error(f"Failed to send failure email: {email_err}")

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(10)
