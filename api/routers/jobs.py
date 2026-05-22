from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from api.models import Job, JobCreate
from api import store

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# pid registry: job_id -> Popen process
_processes: dict[str, subprocess.Popen] = {}
_proc_lock = threading.Lock()


def _launch_job(job: Job, env: dict[str, str]) -> None:
    log_path = Path(job.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    phase_arg = ",".join(str(p) for p in job.phases)
    state_file = str(log_path.parent / "migration_state.json")

    full_env = {**os.environ, **env, "STATE_FILE": state_file}

    store.update_job(
        job.id,
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    with open(log_path, "w") as log_fh:
        proc = subprocess.Popen(
            [sys.executable, "migrate.py", "--phase", phase_arg],
            stdout=log_fh,
            stderr=log_fh,
            env=full_env,
        )

    with _proc_lock:
        _processes[job.id] = proc

    def _wait():
        rc = proc.wait()
        with _proc_lock:
            _processes.pop(job.id, None)
        status_val = "done" if rc == 0 else "failed"
        error = None if rc == 0 else f"Process exited with code {rc}"
        store.update_job(
            job.id,
            status=status_val,
            finished_at=datetime.now(timezone.utc).isoformat(),
            error=error,
        )

    threading.Thread(target=_wait, daemon=True).start()


@router.get("", response_model=list[Job])
def list_jobs():
    return store.list_jobs()


@router.post("", response_model=Job, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate):
    if not payload.phases or not all(1 <= p <= 6 for p in payload.phases):
        raise HTTPException(status_code=422, detail="phases must be a non-empty list of integers 1-6")

    conn = store.get_connection(payload.connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    job = store.create_job(payload, conn.name)
    env = conn.to_env_dict()
    threading.Thread(target=_launch_job, args=(job, env), daemon=True).start()
    return job


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("pending", "running"):
        raise HTTPException(status_code=409, detail=f"Job is already {job.status}")

    with _proc_lock:
        proc = _processes.get(job_id)
    if proc:
        proc.send_signal(signal.SIGTERM)

    store.update_job(
        job_id,
        status="cancelled",
        finished_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/{job_id}/logs")
def stream_logs(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    log_path = Path(job.log_path)

    async def _event_generator():
        pos = 0
        while True:
            if log_path.exists():
                content = log_path.read_text(errors="replace")
                if len(content) > pos:
                    chunk = content[pos:]
                    pos = len(content)
                    for line in chunk.splitlines():
                        yield f"data: {line}\n\n"

            current = store.get_job(job_id)
            if current and current.status in ("done", "failed", "cancelled"):
                yield "event: done\ndata: {}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
