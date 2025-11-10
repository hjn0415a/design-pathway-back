import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/pca", tags=["PCA"])

# ✅ JSON 본문으로 받을 데이터 모델 정의
class PCARequest(BaseModel):
    csv_path: str
    width: float
    height: float
    pointshape: int
    pointsize: float
    text_size: float

@router.post("/")
async def run_pca(req: PCARequest):
    csv_file = Path(req.csv_path).resolve()
    if not csv_file.exists():
        raise HTTPException(status_code=400, detail=f"{csv_file} does not exist.")

    # 출력 파일 경로 (CSV와 동일 폴더에 pca.svg 저장)
    output_path = csv_file.parent / "pca.svg"

    # R 스크립트 경로 (예: backend/rcode/run_pca.R)
    r_script_path = Path(__file__).resolve().parent.parent / "rcode" / "run_pca.R"

    # subprocess 명령어 구성
    cmd = [
        "Rscript",
        str(r_script_path),
        str(csv_file),
        str(req.width),
        str(req.height),
        str(req.pointshape),
        str(req.pointsize),
        str(req.text_size),
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

        # PCA 결과 SVG 파일 반환
        return FileResponse(
            path=output_path,
            media_type="image/svg+xml",
            filename="pca.svg"
        )

    except subprocess.SubprocessError as e:
        raise HTTPException(status_code=500, detail=f"Subprocess error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))