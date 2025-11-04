# fastapi_gsego.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import tempfile
import os

router = APIRouter(prefix="/gsego", tags=["GSEA GO"])

class GseaParams(BaseModel):
    file_path: str
    out_dir: str
    orgdb: str
    min_gs_size: int
    max_gs_size: int
    pvalue_cutoff: float

@router.post("/")
def run_gsea(params: GseaParams):
    try:
        os.makedirs(params.out_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
            r_script_path = tmp_r.name
            tmp_r.write(f"""
library(limma)
library(clusterProfiler)
library({params.orgdb})

file_path <- "{params.file_path}"
out_dir <- "{params.out_dir}"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

df <- read.csv(file_path, check.names = FALSE, stringsAsFactors = FALSE)
stopifnot("Geneid" %in% names(df))

num_cols <- names(df)[vapply(df, is.numeric, logical(1))]
cand <- setdiff(num_cols, c("pvalue","padj","FDR","qvalue","P.Value","p_val","p_val_adj",
                            "log2FC","foldchang","foldchange","foldchge","stat","t","t_stat"))
pattA <- "(^|[^A-Za-z0-9])(A|GroupA|ctrl|control|con|vehicle|veh|untreat|baseline|wt|healthy|pre)($|[^A-Za-z0-9])"
pattB <- "(^|[^A-Za-z0-9])(B|GroupB|case|treated|tx|ko|mut|disease|stim|post|drug)($|[^A-Za-z0-9])"
a_cols <- cand[grepl(pattA, cand, ignore.case = TRUE, perl = TRUE)]
b_cols <- cand[grepl(pattB, cand, ignore.case = TRUE, perl = TRUE)]
stopifnot(length(a_cols) > 1, length(b_cols) > 1)

expr_mat <- as.matrix(df[, c(a_cols, b_cols)])
rownames(expr_mat) <- df$Geneid
if (max(expr_mat, na.rm = TRUE) > 50) expr_mat <- log2(expr_mat + 1)

group <- factor(c(rep("A", length(a_cols)), rep("B", length(b_cols))))
design <- model.matrix(~ 0 + group); colnames(design) <- levels(group)

fit <- lmFit(expr_mat, design)
fit2 <- eBayes(contrasts.fit(fit, makeContrasts(BvsA = B - A, levels = design)))
tval <- fit2$t[, "BvsA"]
geneList <- sort(tval[is.finite(tval)], decreasing = TRUE)

saveRDS(geneList, file = file.path(out_dir, "geneList_t.rds"))
saveRDS(list(geneList = geneList), file = file.path(out_dir, "rank_list.rds"))

for (ont in c("BP","CC","MF")) {{
  gse <- gseGO(geneList = geneList, OrgDb = {params.orgdb}, keyType = "SYMBOL",
               ont = ont, minGSSize = {params.min_gs_size}, maxGSSize = {params.max_gs_size},
               pvalueCutoff = {params.pvalue_cutoff}, pAdjustMethod = "BH", verbose = FALSE)

  saveRDS(gse, file = file.path(out_dir, paste0("gse_", ont, ".rds")))
  if (is.null(gse) || is.null(gse@result) || nrow(gse@result) == 0) {{
    write.csv(data.frame(), file = file.path(out_dir, paste0("gse_", ont, ".csv")), row.names = FALSE)
    next
  }}
  write.csv(as.data.frame(gse), file = file.path(out_dir, paste0("gse_", ont, ".csv")), row.names = FALSE)
}}
""")

        result = subprocess.run(
            ["Rscript", r_script_path],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode == 0:
            return {"message": "GSEA pipeline completed successfully!", "stdout": result.stdout}
        else:
            raise HTTPException(status_code=500, detail=result.stderr)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))