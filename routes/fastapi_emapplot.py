# fastapi_emapplot.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import tempfile
import os

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
    if not req.combo_names:
        raise HTTPException(status_code=400, detail="No combo names provided")

    combos_r = "c(" + ",".join([f'"{c}"' for c in req.combo_names]) + ")"

    r_code = f"""
library(clusterProfiler)
library(enrichplot)
library(ggplot2)
library(svglite)

.make_find_ego <- function(combo_dir, ont) {{
  direct <- file.path(combo_dir, sprintf("GO_%s_ego.rds", ont))
  if (file.exists(direct)) return(direct)
  cand <- list.files(combo_dir,
                     pattern = paste0("^GO_", ont, "_ego\\\\.rds$"),
                     recursive = TRUE, full.names = TRUE)
  if (length(cand) >= 1) return(cand[1])
  return(NA_character_)
}}

make_emap_from_rds_by_combo <- function(result_root,
                                        figure_root,
                                        combo_names,
                                        onts     = c("BP","CC","MF"),
                                        show_n   = {req.show_n},
                                        width    = {req.plot_width},
                                        height   = {req.plot_height},
                                        pie      = FALSE,
                                        layout   = "kk") {{
  if (!dir.exists(figure_root)) dir.create(figure_root, recursive = TRUE)

  for (nm in combo_names) {{
    combo_dir <- file.path(result_root, nm)
    out_dir   <- file.path(figure_root, nm)
    if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

    for (ont in onts) {{
      rds_path <- .make_find_ego(combo_dir, ont)
      if (is.na(rds_path)) next

      ego <- readRDS(rds_path)
      if (is.null(ego) || is.null(ego@result) || nrow(ego@result) < 2) next

      ego_sim <- tryCatch(pairwise_termsim(ego), error = function(e) NULL)
      if (is.null(ego_sim) || is.null(ego_sim@result) || nrow(ego_sim@result) < 2) next

      k <- min(show_n, nrow(ego_sim@result))
      p <- emapplot(ego_sim, showCategory = k, layout = layout, pie = pie)

      out_svg <- file.path(out_dir, sprintf("emap_%s.svg", ont))
      ggsave(out_svg, p, width = width, height = height, device = svglite::svglite)
    }}
  }}
}}

combo_names <- {combos_r}

make_emap_from_rds_by_combo(
  result_root = "{req.result_root}",
  figure_root = "{req.figure_root}",
  combo_names = combo_names
)
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
        tmp_r.write(r_code)
        tmp_r_path = tmp_r.name

    try:
        result = subprocess.run(["Rscript", tmp_r_path], capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            return {"status": "success", "stdout": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=result.stderr)
    finally:
        os.remove(tmp_r_path)