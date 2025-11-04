from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import subprocess

router = APIRouter(prefix="/heatmap", tags=["heatmap"])

@router.post("/")
async def run_heatmap(
    csv_path: str = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    top_n_genes: int = Form(...)
):
    csv_file = Path(csv_path).resolve()
    if not csv_file.exists():
        raise HTTPException(status_code=400, detail=f"{csv_file} does not exist.")

    # 출력 파일 경로
    output_path = csv_file.parent / "heatmap2.svg"

    # R 스크립트 경로 (예: backend/scripts/run_heatmap.R)
    r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_heatmap.R"

    # subprocess 명령어 구성
    cmd = [
        "Rscript",
        str(r_script_path),
        str(csv_file),
        str(width),
        str(height),
        str(top_n_genes),
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, text=True, capture_output=True)

        if result.returncode != 0:
            print("❌ Rscript stderr:")
            print(result.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Rscript execution failed:\n{result.stderr}"
            )

        if not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Rscript finished but no SVG file was generated."
            )

        return FileResponse(
            path=output_path,
            media_type="image/svg+xml",
            filename="heatmap.svg"
        )

    except subprocess.SubprocessError as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))