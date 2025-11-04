# backend/routes/fastapi_pca.py
import os
import tempfile
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess

router = APIRouter(
    prefix="/pca",
    tags=["PCA"]
)

class PCARequest(BaseModel):
    csv_path: str
    output_svg: str
    width: float = 8.0
    height: float = 6.0
    pointshape: int = 16
    pointsize: float = 3.5
    text_size: float = 4.0

@router.post("/", response_class=None)  # SVG 파일을 바이너리로 반환
def run_pca(request: PCARequest):
    csv_path = request.csv_path
    output_svg = request.output_svg
    width = request.width
    height = request.height
    pointshape = request.pointshape
    pointsize = request.pointsize
    text_size = request.text_size

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=400, detail=f"CSV file not found: {csv_path}")

    # 임시 R 스크립트 생성
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
        r_script_path = tmp_r.name
        tmp_r.write(f"""
library(readr)
library(factoextra)
library(ggrepel)
library(svglite)

dat <- as.data.frame(read_csv("{csv_path}"))

# 샘플 열 추출 (Geneid, foldchange, pvalue 제외)
sample_cols <- grep("(^Group)|(_[0-9]+$)", names(dat), value = TRUE)
X <- t(as.matrix(dat[, sample_cols, drop = FALSE]))
rownames(X) <- sample_cols

Xz <- scale(X, center = TRUE, scale = TRUE)
Xz <- Xz[, colSums(is.na(Xz)) == 0, drop = FALSE]

pca_res <- prcomp(Xz, center = FALSE, scale. = FALSE)
rownames(pca_res$x) <- rownames(X)
sample_groups <- factor(sub("(_[0-9]+$)|([0-9]+$)", "", rownames(pca_res$x)))
df <- data.frame(PC1 = pca_res$x[,1], PC2 = pca_res$x[,2],
                 sample = rownames(pca_res$x), group = sample_groups)

svglite("{output_svg}", width = {width}, height = {height})

p <- fviz_pca_ind(
  pca_res,
  geom.ind   = "point",
  col.ind    = sample_groups,
  pointshape = {pointshape},
  pointsize  = {pointsize},
  mean.point = FALSE,
  addEllipses= FALSE
) +
  geom_text_repel(data = df, aes(PC1, PC2, label = sample, color = group),
                  size = {text_size}, show.legend = FALSE)

print(p)
dev.off()
""")

    # Rscript 실행
    try:
        subprocess.run(["Rscript", r_script_path], check=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"R script execution failed: {e}")
    finally:
        os.remove(r_script_path)

    # 생성된 SVG 반환
    if not os.path.exists(output_svg):
        raise HTTPException(status_code=500, detail=f"PCA SVG not generated: {output_svg}")

    with open(output_svg, "rb") as f:
        content = f.read()
    return content