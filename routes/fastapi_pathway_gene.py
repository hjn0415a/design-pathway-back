import os
import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import zipfile
import io

router = APIRouter(
    prefix="/pathway_gene",
    tags=["PathwayGene"]
)

class PathwayGeneRequest(BaseModel):
    edox_dir: str
    csv_path: str
    output_dir: str
    top_pathways: int = 5
    top_genes_per_pathway: int = 20
    width: float = 12.0
    height: float = 6.0
    max_setsize: int = 50

@router.post("/", response_class=None)  # ZIP 바이너리 반환
def run_pathway_heatplot(request: PathwayGeneRequest):
    # 요청값
    edox_dir = request.edox_dir
    csv_path = request.csv_path
    output_dir = request.output_dir
    top_pathways = request.top_pathways
    top_genes = request.top_genes_per_pathway
    width = request.width
    height = request.height
    max_setsize = request.max_setsize

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=400, detail=f"CSV file not found: {csv_path}")
    if not os.path.exists(edox_dir):
        raise HTTPException(status_code=400, detail=f"Edox directory not found: {edox_dir}")
    os.makedirs(output_dir, exist_ok=True)

    # R 스크립트 경로
    r_script_path = os.path.join(os.path.dirname(__file__), "../../r/run_pathway_gene.R")
    if not os.path.exists(r_script_path):
        raise HTTPException(status_code=500, detail=f"R script not found: {r_script_path}")

    # subprocess 호출
    cmd = [
        "Rscript",
        r_script_path,
        csv_path,
        edox_dir,
        output_dir,
        str(top_pathways),
        str(top_genes),
        str(width),
        str(height),
        str(max_setsize)
    ]

    try:
        subprocess.run(cmd, check=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"R script execution failed: {e}")

    # 생성된 SVG들을 ZIP으로 반환
    svg_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".svg")]
    if not svg_files:
        raise HTTPException(status_code=500, detail="No heatplot SVGs generated.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for f in svg_files:
            zipf.write(f, arcname=os.path.basename(f))
    zip_buffer.seek(0)
    return zip_buffer.read()