from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
import os

router = APIRouter(prefix="/gseaplot", tags=["GSEA Plot"])

class GSEAPayload(BaseModel):
    input_dir: str
    output_dir: str
    topN: int = 10
    width: float = 12.0
    height: float = 8.0
    ont: str = "BP"
    idx: int = 1

# ----------------- Total gseaplot2 -----------------
@router.post("/total")
def run_gseaplot_total(payload: GSEAPayload):
    os.makedirs(payload.output_dir, exist_ok=True)
    r_script_path = os.path.join(os.path.dirname(__file__), "../../r/run_gseaplot_total.R")
    if not os.path.exists(r_script_path):
        return {"error": f"R script not found: {r_script_path}"}

    cmd = [
        "Rscript",
        r_script_path,
        payload.input_dir,
        payload.output_dir,
        str(payload.topN),
        str(payload.width),
        str(payload.height)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return {"error": result.stderr}
    return {"message": "Total gseaplot2 generation completed!"}

# ----------------- GSEA Term Plot -----------------
@router.post("/term")
def run_gseaplot_term(payload: GSEAPayload):
    os.makedirs(payload.output_dir, exist_ok=True)
    r_script_path = os.path.join(os.path.dirname(__file__), "../../r/run_gseaplot_term.R")
    if not os.path.exists(r_script_path):
        return {"error": f"R script not found: {r_script_path}"}

    cmd = [
        "Rscript",
        r_script_path,
        payload.input_dir,
        payload.output_dir,
        str(payload.width),
        str(payload.height),
        payload.ont,
        str(payload.idx)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return {"error": result.stderr}
    return {"message": f"GSEA Term plot ({payload.ont}, idx={payload.idx}) completed!"}