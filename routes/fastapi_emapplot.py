from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import os
from pathlib import Path

router = APIRouter(prefix="/emapplot", tags=["Emapplot"])

class EmapRequest(BaseModel):
    result_root: str
    figure_root: str
    combo_names: list[str]
    show_n: int
    plot_width: float
    plot_height: float

@router.post("/")
def run_emapplot(req: EmapRequest):
    """Run emapplot generation using external R script."""
    if not req.combo_names:
        raise HTTPException(status_code=400, detail="No combo names provided")

    combos_r = "c(" + ",".join([f'"{c}"' for c in req.combo_names]) + ")"

    # ✅ R 스크립트 경로 (예: backend/rcode/run_emapplot.R)
    r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_emapplot.R"

    try:
        cmd = [
            "Rscript",
            str(r_script_path),
            req.result_root,
            req.figure_root,
            combos_r,
            str(req.show_n),
            str(req.plot_width),
            str(req.plot_height),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        if result.returncode == 0:
            return {"status": "success", "stdout": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=result.stderr)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))