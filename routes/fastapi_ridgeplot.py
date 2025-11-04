# fastapi_ridgeplot.py
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
import subprocess
import tempfile
import os

router = APIRouter(prefix="/ridgeplot", tags=["Ridgeplot"])

@router.post("/")
async def run_ridgeplot(
    input_file: str = Form(...),
    output_dir: str = Form(...),
    width: float = Form(...),
    height: float = Form(...)
):
    try:
        os.makedirs(output_dir, exist_ok=True)

        # 임시 R 스크립트 파일 생성
        with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
            r_script_path = tmp_r.name
            tmp_r.write(f"""
library(limma)
library(clusterProfiler)
library(org.Hs.eg.db)
library(enrichplot)
library(ggplot2)

file_path <- "{input_file}"
out_dir   <- "{output_dir}"
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

group  <- factor(c(rep("A", length(a_cols)), rep("B", length(b_cols))))
design <- model.matrix(~ 0 + group); colnames(design) <- levels(group)

fit  <- lmFit(expr_mat, design)
fit2 <- eBayes(contrasts.fit(fit, makeContrasts(BvsA = B - A, levels = design)))
tval <- fit2$t[, "BvsA"]
geneList <- sort(tval[is.finite(tval)], decreasing = TRUE)

rank_list <- list(
  method   = "limma_moderated_t (BvsA)",
  a_cols   = a_cols,
  b_cols   = b_cols,
  geneList = geneList
)
saveRDS(rank_list, file = file.path(out_dir, "rank_list.rds"))
saveRDS(geneList,  file.path(out_dir, "geneList_t.rds"))

for (ont in c("BP","CC","MF")) {{
  gse <- gseGO(geneList = geneList, OrgDb = org.Hs.eg.db, keyType = "SYMBOL",
               ont = ont, minGSSize = 10, maxGSSize = 500,
               pvalueCutoff = 0.05, pAdjustMethod = "BH", verbose = FALSE)
  saveRDS(gse, file = file.path(out_dir, paste0("gse_", ont, ".rds")))
  if (is.null(gse) || nrow(gse@result) == 0) next
  p <- ridgeplot(gse, showCategory = 20, fill = "p.adjust", label_format = 40) +
       labs(title = paste("GSEA Ridgeplot (GO:", ont, ")"),
            x = "enrichment distribution") +
       theme_bw()
  ggsave(file.path(out_dir, paste0("ridgeplot_", ont, ".svg")),
         p, width = {width}, height = {height}, device = "svg")
}}
""")

        # Rscript 실행
        result = subprocess.run(
            ["Rscript", r_script_path],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode == 0:
            return JSONResponse(content={"message": "Ridgeplot GSEA completed successfully!", "stdout": result.stdout})
        else:
            raise HTTPException(status_code=500, detail=result.stderr)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))