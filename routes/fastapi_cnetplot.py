from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import tempfile
import os
import pandas as pd
import shutil

# ✅ prefix를 /api로 시작하도록 변경
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
    combo_csv = os.path.join(req.combo_root, "combo_names.csv")
    if not os.path.exists(combo_csv):
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

    r_code = f"""
library(clusterProfiler)
library(enrichplot)
library(ggplot2)
library(svglite)

.find_ego_rds <- function(combo_dir, ont) {{
  direct <- file.path(combo_dir, sprintf("GO_%s_ego.rds", ont))
  if (file.exists(direct)) return(direct)
  cand <- list.files(combo_dir, pattern = paste0("^GO_", ont, "_ego\\\\.rds$"), recursive = TRUE, full.names = TRUE)
  if (length(cand) >= 1) return(cand[1])
  NA_character_
}}

make_cnet_from_rds_by_combo <- function(result_root, figure_root, combo_names,
                                        onts=c("BP","CC","MF"), show_n={req.showCategory},
                                        width={req.plot_width}, height={req.plot_height},
                                        circular=TRUE, layout="kk") {{
  if (!dir.exists(figure_root)) dir.create(figure_root, recursive=TRUE)
  for (nm in combo_names) {{
    combo_dir <- file.path(result_root, nm)
    out_dir   <- file.path(figure_root, nm)
    if (!dir.exists(out_dir)) dir.create(out_dir, recursive=TRUE)
    for (ont in onts) {{
      rds_path <- .find_ego_rds(combo_dir, ont)
      if (is.na(rds_path)) next
      ego <- readRDS(rds_path)
      if (is.null(ego) || is.null(ego@result) || nrow(ego@result) < 1) next
      k <- min(show_n, nrow(ego@result))
      p <- cnetplot(ego, showCategory=k, circular=circular, layout=layout)
      ggsave(file.path(out_dir, sprintf("cnet_%s.svg", ont)), p,
             width=width, height=height, device=svglite::svglite)
    }}
  }}
}}

combo_names <- {combos_r}
make_cnet_from_rds_by_combo("{req.result_root}", "{req.figure_root}", combo_names)
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False) as tmp_r:
            tmp_r.write(r_code)
            tmp_r_path = tmp_r.name

        result = subprocess.run(["Rscript", tmp_r_path], capture_output=True, text=True)
        os.remove(tmp_r_path)

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