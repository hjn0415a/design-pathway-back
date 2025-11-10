from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import tempfile
import os
import pandas as pd
import shutil
from pathlib import Path

router = APIRouter(prefix="/api/cnetplot", tags=["Cnetplot"])

class CnetRequest(BaseModel):
    result_root: str
    figure_root: str
    combo_root: str
    fc_threshold: float
    pval_threshold: float
    showCategory: int
    plot_width: float
    plot_height: float

@router.post("/")
def run_cnetplot(req: CnetRequest):
    """Run Cnetplot generation using an external R script."""
    combo_csv = Path(req.combo_root) / "combo_names.csv"
    if not combo_csv.exists():
        raise HTTPException(status_code=404, detail="combo_names.csv not found")

    combo_df = pd.read_csv(combo_csv)
    selected_combos = [
        c for c in combo_df["combo"]
        if float(c.split("_")[0][2:]) == req.fc_threshold
        and float(c.split("_")[1][1:]) == req.pval_threshold
    ]

    if not selected_combos:
        raise HTTPException(status_code=400, detail="No matching combos found")

    os.makedirs(req.figure_root, exist_ok=True)
    combos_r = 'c(' + ','.join([f'"{c}"' for c in selected_combos]) + ')'

    # ✅ R 스크립트 경로 지정 (예: backend/rcode/run_cnetplot.R)
    r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_cnetplot.R"

    try:
        # Rscript 실행 명령어 구성
        cmd = [
            "Rscript",
            str(r_script_path),
            req.result_root,
            req.figure_root,
            combos_r,
            str(req.showCategory),
            str(req.plot_width),
            str(req.plot_height),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        # ✅ ZIP 파일 생성
        zip_path = os.path.join(req.figure_root, "Cnetplots_combos.zip")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        shutil.make_archive(zip_path.replace(".zip", ""), "zip", req.figure_root)

        return {"message": "Cnetplot generation completed.", "zip_path": zip_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))