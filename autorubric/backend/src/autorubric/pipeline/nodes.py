from .state import PipelineState
from autorubric.contracts import JobStatus
from autorubric.extraction import extract
from autorubric.nlp import segment
from autorubric.retrieval import match, embed_propositions
from autorubric.evaluator import classify
from autorubric.audit import audit
from autorubric.scorer import score, SCORER_VERSION
from autorubric.annotation import annotate
from autorubric.core.config import config
import datetime
import json
import asyncio
import concurrent.futures
from functools import wraps


def _run_sync(coro):
    """Run an async coroutine from sync code safely handling active event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def track_stage(stage_name: str, new_status: JobStatus):
    def decorator(func):
        @wraps(func)
        def wrapper(state: PipelineState):
            job_id = state.get("doc_id", "unknown")
            started_at = datetime.datetime.now(datetime.UTC)
            state["status"] = new_status
            
            from autorubric.core.db import AsyncSessionLocal, Job, JobEvent
            
            async def log_start():
                try:
                    async with AsyncSessionLocal() as session:
                        import uuid
                        job = await session.get(Job, job_id)
                        if job:
                            job.status = new_status
                        event = JobEvent(id=str(uuid.uuid4()), job_id=job_id, stage=stage_name, started_at=started_at)
                        session.add(event)
                        await session.commit()
                except Exception:
                    pass
            
            try:
                _run_sync(log_start())
            except Exception:
                pass
            
            try:
                new_state = func(state)
                
                async def log_success():
                    try:
                        async with AsyncSessionLocal() as session:
                            from sqlalchemy import select
                            stmt = select(JobEvent).where(JobEvent.job_id == job_id, JobEvent.stage == stage_name).order_by(JobEvent.started_at.desc())
                            event = (await session.execute(stmt)).scalars().first()
                            if event:
                                event.finished_at = datetime.datetime.now(datetime.UTC)
                                event.ok = True
                            await session.commit()
                    except Exception:
                        pass
                
                try:
                    _run_sync(log_success())
                except Exception:
                    pass
                
                return new_state
            except Exception as e:
                async def log_failure():
                    try:
                        async with AsyncSessionLocal() as session:
                            from sqlalchemy import select
                            stmt = select(JobEvent).where(JobEvent.job_id == job_id, JobEvent.stage == stage_name).order_by(JobEvent.started_at.desc())
                            event = (await session.execute(stmt)).scalars().first()
                            if event:
                                event.finished_at = datetime.datetime.now(datetime.UTC)
                                event.ok = False
                                event.error = str(e)
                            await session.commit()
                    except Exception:
                        pass
                        
                try:
                    _run_sync(log_failure())
                except Exception:
                    pass
                raise
        return wrapper
    return decorator


@track_stage("extract", JobStatus.EXTRACTING)
def node_extract(state: PipelineState):
    from autorubric.extraction import extract
    state["tokens"] = extract(state["pdf_bytes"])
    return state


@track_stage("segment", JobStatus.SEGMENTING)
def node_segment(state: PipelineState):
    from autorubric.nlp import segment
    propositions = segment(state["tokens"], doc_id=state.get("doc_id", ""))
    
    # Set from_hidden_text on propositions
    token_dict = {t.id: t for t in state["tokens"]}
    for prop in propositions:
        if not prop.from_hidden_text:
            if any(token_dict.get(tid) and token_dict[tid].is_hidden for tid in prop.token_ids):
                prop.from_hidden_text = True
                
    state["propositions"] = propositions
    
    # Store embed_propositions output in job_artifacts
    from autorubric.retrieval import embed_propositions
    embeddings = embed_propositions(propositions)
        
    from autorubric.core.db import AsyncSessionLocal, JobArtifact
    
    async def save_artifact():
        try:
            async with AsyncSessionLocal() as session:
                art = JobArtifact(
                    id=f"art-{state.get('doc_id')}-embed",
                    job_id=state.get("doc_id", "unknown"),
                    stage="segment",
                    payload={"embeddings": embeddings}
                )
                session.add(art)
                await session.commit()
        except Exception:
            pass
            
    try:
        _run_sync(save_artifact())
    except Exception:
        pass
    
    return state


@track_stage("retrieve", JobStatus.RETRIEVING)
def node_retrieve(state: PipelineState):
    from autorubric.retrieval import match
    state["candidates"] = match(state["propositions"], state["rubric"])
    return state


# EvalPairs helper
class EvalPairAdapter:
    def __init__(self, prop_id, criterion_id, proposition_text, criterion_text, similarity):
        self.prop_id = prop_id
        self.criterion_id = criterion_id
        self.proposition_text = proposition_text
        self.criterion_text = criterion_text
        self.similarity = similarity
        
    def __getattr__(self, name):
        if name in ["prop_id", "criterion_id", "similarity"]:
            return self.__dict__[name]
        raise AttributeError(name)


@track_stage("evaluate", JobStatus.EVALUATING)
def node_evaluate(state: PipelineState):
    prop_dict = {p.id: p for p in state.get("propositions", [])}
    crit_dict = {c.id: c for c in state["rubric"].criteria}
    
    eval_pairs = []
    eval_pairs_dict = []
    for cand in state.get("candidates", []):
        p_text = prop_dict[cand.prop_id].text if cand.prop_id in prop_dict else ""
        c_text = crit_dict[cand.criterion_id].description if cand.criterion_id in crit_dict else ""
        eval_pairs_dict.append({
            "prop_id": cand.prop_id,
            "criterion_id": cand.criterion_id,
            "similarity": cand.similarity
        })
        from autorubric.contracts import EvalPair
        eval_pairs.append(EvalPair(
            prop_id=cand.prop_id,
            criterion_id=cand.criterion_id,
            proposition_text=p_text,
            criterion_text=c_text,
            similarity=cand.similarity
        ))
        
    try:
        from autorubric.workers.tasks import evaluate_task
        from celery.result import allow_join_result
        from autorubric.contracts import Classification
        
        with allow_join_result():
            result_json = evaluate_task.delay(eval_pairs_dict).get(timeout=5)
            classifications = [Classification.model_validate(c) for c in result_json]
    except Exception:
        from autorubric.evaluator import classify
        classifications = classify(eval_pairs)
        
    state["classifications"] = classifications
    return state


@track_stage("audit", JobStatus.AUDITING)
def node_audit(state: PipelineState):
    from autorubric.audit import audit
    state["verdicts"] = audit(state.get("classifications", []), state.get("tokens", []), state.get("propositions", []))
    return state


@track_stage("score", JobStatus.SCORING)
def node_score(state: PipelineState):
    state["audit_bundle"] = {
        "rubric": state["rubric"].model_dump(),
        "classifications": [c.model_dump() for c in state.get("classifications", [])],
        "verdicts": [v.model_dump() for v in state.get("verdicts", [])],
        "scorer_version": SCORER_VERSION
    }
    
    score_res = score(state.get("classifications", []), state["rubric"], state.get("verdicts", []))
    score_res.doc_id = state.get("doc_id", "unknown")
    state["score"] = score_res
    
    if score_res.needs_review:
        state["status"] = JobStatus.NEEDS_REVIEW
    return state


@track_stage("annotate", JobStatus.ANNOTATING)
def node_annotate(state: PipelineState):
    from autorubric.annotation import annotate
    pdf_bytes = annotate(state["pdf_bytes"], state["score"])
        
    # Save the annotated pdf to the volume
    import os
    
    doc_id = state.get("doc_id", "unknown")
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    pdf_path = os.path.join(config.UPLOADS_DIR, f"{doc_id}_annotated.pdf")
    
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
        
    state["annotated_pdf"] = pdf_path
    if state["status"] != JobStatus.NEEDS_REVIEW:
        state["status"] = JobStatus.DONE
    return state
