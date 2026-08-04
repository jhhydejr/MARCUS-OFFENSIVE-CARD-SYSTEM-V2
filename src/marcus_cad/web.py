from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .batch import compile_batch
from .pdf_packet import PdfPacketError, create_blocked_calls_report, merge_pdfs
from .pipeline import PipelineController
from .system import MarcusSystem

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_OUTPUT_ROOT = PROJECT_ROOT / "output" / "web"
WEB_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Marcus Offensive CAD", version="4.0.0")
system = MarcusSystem(PROJECT_ROOT)
pipeline = PipelineController(system)


class PdfRequest(BaseModel):
    call: str = Field(min_length=1, max_length=20000)
    card_type: str = "FORMATION_CARD"
    require_assignments: bool = False


def _safe_job_id(value: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        raise HTTPException(status_code=404, detail="Unknown job")
    return value


def _job_dir(job_id: str) -> Path:
    job = (WEB_OUTPUT_ROOT / _safe_job_id(job_id)).resolve()
    if WEB_OUTPUT_ROOT.resolve() not in job.parents:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job


def _read_validation(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "application": "Marcus Offensive CAD PDF"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marcus Offensive CAD</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f3f5f7;color:#111}.wrap{max-width:960px;margin:auto;padding:24px}
.panel{background:#fff;border:1px solid #ccd2d8;border-radius:10px;padding:20px;margin-bottom:18px;box-shadow:0 2px 8px #0001}
h1{margin:0 0 8px}.sub{color:#555}.row{display:grid;grid-template-columns:1fr 220px;gap:12px}label{font-weight:700;display:block;margin-bottom:7px}
textarea,select{width:100%;box-sizing:border-box;font-size:18px;padding:12px;border:1px solid #9da7b1;border-radius:6px}textarea{min-height:310px;resize:vertical}
button{background:#111;color:#fff;border:0;border-radius:6px;padding:15px 26px;font-size:19px;font-weight:700;cursor:pointer;margin-top:14px}button:disabled{opacity:.5}
#status{font-weight:700;margin:14px 0}.ok{color:#087b22}.bad{color:#b00020}.download{font-size:20px;font-weight:700;display:inline-block;margin:8px 0}
.result{border-top:1px solid #ddd;padding:10px 0}.small{font-family:monospace;white-space:pre-wrap;background:#f6f7f8;padding:12px;border-radius:6px;max-height:350px;overflow:auto}
@media(max-width:700px){.row{grid-template-columns:1fr}}
</style></head><body><main class="wrap">
<div class="panel"><h1>Marcus Offensive CAD</h1><div class="sub">Paste one call per line. Generate one printable PDF packet.</div></div>
<div class="panel"><div class="row"><div><label for="call">Calls</label><textarea id="call" placeholder="EX. PLAY CALL"></textarea></div>
<div><label for="type">Card Type</label><select id="type"><option value="FORMATION_CARD" selected>Formation Card</option><option value="SCOUT_CARD">Scout Card</option><option value="PLAY_CARD">Play Card</option></select></div></div>
<button id="generate" type="button">GENERATE PDF</button><div id="status"></div><div id="download"></div><div id="results"></div><div id="details" class="small" hidden></div></div>
<script>
const button=document.getElementById('generate'),input=document.getElementById('call'),type=document.getElementById('type'),statusEl=document.getElementById('status'),download=document.getElementById('download'),results=document.getElementById('results'),details=document.getElementById('details');
input.addEventListener('focus',()=>input.placeholder='');input.addEventListener('blur',()=>{if(!input.value.trim())input.placeholder='EX. PLAY CALL'});
button.addEventListener('click',async()=>{const call=input.value.trim();if(!call){statusEl.textContent='ENTER AT LEAST ONE CALL';statusEl.className='bad';return}button.disabled=true;statusEl.textContent='GENERATING PDF...';statusEl.className='';download.innerHTML='';results.innerHTML='';details.hidden=true;
try{const response=await fetch('/api/pdf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({call,card_type:type.value})});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail||data));statusEl.textContent=data.blocked?'PDF READY - SOME CALLS BLOCKED':'PDF READY';statusEl.className=data.blocked?'bad':'ok';
if(data.packet_pdf){const a=document.createElement('a');a.className='download';a.href=data.packet_pdf;a.textContent='DOWNLOAD PDF PACKET';a.target='_blank';download.appendChild(a)}
(data.items||[]).forEach(item=>{const div=document.createElement('div');div.className='result';div.textContent=`${item.index}. ${item.success?'GENERATED':'BLOCKED'} - ${item.call}`;div.classList.add(item.success?'ok':'bad');results.appendChild(div)});details.textContent=JSON.stringify(data.summary||{},null,2);details.hidden=false;
}catch(error){statusEl.textContent='SERVER ERROR';statusEl.className='bad';details.textContent=String(error);details.hidden=false}finally{button.disabled=false}});
</script></main></body></html>"""


@app.post("/api/pdf")
def generate_pdf(request: PdfRequest) -> dict[str, Any]:
    calls = [line.strip() for line in request.call.splitlines() if line.strip()]
    if not calls:
        raise HTTPException(status_code=422, detail="Enter at least one non-empty call.")

    job_id = uuid.uuid4().hex
    job_dir = _job_dir(job_id)
    items: list[dict[str, Any]] = []
    pdf_paths: list[Path] = []

    if len(calls) == 1:
        result = pipeline.compile_play(calls[0], job_dir / "01", card_type=request.card_type, require_assignments=request.require_assignments)
        validation = _read_validation(job_dir / "01" / "validation.json")
        pdf_path = job_dir / "01" / "card.pdf"
        if result.success and pdf_path.is_file():
            pdf_paths.append(pdf_path)
        items.append({"index": 1, "call": calls[0], "success": result.success, "validation": validation, "error": result.error})
    else:
        summary = compile_batch(system, calls, job_dir, card_type=request.card_type, require_assignments=request.require_assignments)
        for item in summary.items:
            item_dir = job_dir / item.output_directory
            pdf_path = item_dir / "card.pdf"
            if item.renderable and pdf_path.is_file():
                pdf_paths.append(pdf_path)
            items.append({"index": item.index, "call": item.source_call, "success": item.renderable, "blockers": item.blockers})

    blocked_items = [
        (item["index"], item["call"], item.get("blockers", []))
        for item in items
        if not item["success"]
    ]
    if blocked_items:
        report_path = create_blocked_calls_report(
            blocked_items, job_dir / "Blocked_Calls_Report.pdf"
        )
        pdf_paths.append(report_path)

    packet_path = job_dir / "Marcus_CAD_Packet.pdf"
    try:
        merge_pdfs(pdf_paths, packet_path)
    except PdfPacketError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    blocked = sum(not item["success"] for item in items)
    return {
        "job_id": job_id,
        "packet_pdf": f"/files/{job_id}/Marcus_CAD_Packet.pdf",
        "blocked": blocked,
        "summary": {"total": len(items), "generated": len(items) - blocked, "blocked": blocked},
        "items": items,
    }


@app.post("/api/draw")
def legacy_draw(request: PdfRequest) -> dict[str, Any]:
    """Backward-compatible single-card endpoint for existing clients/tests."""
    calls = [line.strip() for line in request.call.splitlines() if line.strip()]
    if len(calls) != 1:
        raise HTTPException(status_code=422, detail="Use /api/pdf for multiple calls.")
    job_id = uuid.uuid4().hex
    job_dir = _job_dir(job_id)
    result = pipeline.compile_play(
        calls[0],
        job_dir,
        card_type=request.card_type,
        require_assignments=request.require_assignments,
    )
    validation = _read_validation(job_dir / "validation.json")
    files = {}
    pdf_path = job_dir / "card.pdf"
    if pdf_path.is_file():
        files["card.pdf"] = f"/files/{job_id}/card.pdf"
    return {
        "job_id": job_id,
        "success": result.success,
        "source_call": result.source_call,
        "normalized_call": result.normalized_call,
        "error": result.error,
        "files": files,
        "validation": validation,
    }


@app.get("/files/{job_id}/card.pdf")
def get_single_pdf(job_id: str) -> FileResponse:
    path = (_job_dir(job_id) / "card.pdf").resolve()
    if _job_dir(job_id) not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Card PDF not found")
    return FileResponse(path, filename="card.pdf", media_type="application/pdf")


@app.get("/files/{job_id}/Marcus_CAD_Packet.pdf")
def get_packet(job_id: str) -> FileResponse:
    path = (_job_dir(job_id) / "Marcus_CAD_Packet.pdf").resolve()
    if _job_dir(job_id) not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="PDF packet not found")
    return FileResponse(path, filename="Marcus_CAD_Packet.pdf", media_type="application/pdf")
