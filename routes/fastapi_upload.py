# fastapi_upload.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path

router = APIRouter(prefix="/upload-csv", tags=["Upload CSV"])

@router.post("/")
async def upload_csv(file: UploadFile = File(...), target_dir: str = Form(...)):
    try:
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)  # 경로 없으면 생성

        file_path = target_path / file.filename
        with open(file_path, "wb") as f:
            f.write(await file.read())

        return {"message": f"{file.filename} saved successfully at {file_path}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))