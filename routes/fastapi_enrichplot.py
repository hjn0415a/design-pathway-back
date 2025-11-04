import os
import subprocess
import tempfile
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/enrichplot", tags=["Enrichplot"])

class EnrichplotParams(BaseModel):
    result_root: str
    output_root: str
    showCategory: int
    pvalueCutoff: float
    org_db: str
    plot_width: float
    plot_height: float

@router.post("")
def run_enrichplot(params: EnrichplotParams):
    """Run GO enrichment analysis using R script."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tmp_r:
        r_script_path = tmp_r.name

        tmp_r.write(f"""
library(clusterProfiler)
library({params.org_db})
library(enrichplot)
library(ggplot2)

run_enrich_genedi_min <- function(result_root,
                                  output_root,
                                  combo_names,
                                  file_name    = "filtered_gene_list.csv",
                                  showCategory = {params.showCategory},
                                  p_cut        = {params.pvalueCutoff},
                                  save_ego     = TRUE,
                                  width        = {params.plot_width},
                                  height       = {params.plot_height}) {{

    for (nm in combo_names) {{
        combo_dir_in <- file.path(result_root, nm)
        f <- file.path(combo_dir_in, file_name)
        if (!file.exists(f)) next

        df <- read.csv(f, check.names = FALSE, stringsAsFactors = FALSE)
        sym_col <- grep("^(Geneid|Gene_Symbol|SYMBOL)$", names(df),
                        ignore.case = TRUE, value = TRUE)[1]
        if (is.na(sym_col)) next

        conv <- tryCatch(
            bitr(df[[sym_col]], fromType = "SYMBOL", toType = "ENTREZID",
                 OrgDb = {params.org_db}),
            error = function(e) {{ NULL }}
        )
        if (is.null(conv) || !"ENTREZID" %in% names(conv)) next

        ids <- unique(na.omit(conv$ENTREZID))
        if (!length(ids)) next

        combo_dir_out <- file.path(output_root, nm)
        fig_dir <- file.path(combo_dir_out, "figure")
        if (!dir.exists(fig_dir)) dir.create(fig_dir, recursive = TRUE)

        for (ont in c("BP", "CC", "MF")) {{
            ego <- suppressMessages(
                enrichGO(
                    gene           = ids,
                    OrgDb          = {params.org_db},
                    keyType        = "ENTREZID",
                    ont            = ont,
                    pAdjustMethod  = "BH",
                    pvalueCutoff   = p_cut,
                    qvalueCutoff   = 1,
                    readable       = TRUE
                )
            )

            if (!is.null(ego) && !is.null(ego@result) && nrow(ego@result) > 0) {{
                write.csv(ego@result,
                          file.path(combo_dir_out, sprintf("GO_%s_result.csv", ont)),
                          row.names = FALSE)
                p <- dotplot(ego, showCategory = showCategory,
                             x = "GeneRatio", color = "p.adjust") +
                     ggtitle(sprintf("GO %s - %s", ont, nm))
                ggsave(file.path(fig_dir, sprintf("GO_%s.svg", ont)),
                       p, width = width, height = height)
                if (isTRUE(save_ego)) {{
                    saveRDS(ego, file.path(combo_dir_out, sprintf("GO_%s_ego.rds", ont)))
                }}
            }}
        }}
    }}
}}

combo_names <- readRDS(file.path("{params.result_root}", "combo_names.rds"))

run_enrich_genedi_min(
    result_root = "{params.result_root}",
    output_root = "{params.output_root}",
    combo_names = combo_names,
    showCategory = {params.showCategory},
    p_cut = {params.pvalueCutoff},
    width = {params.plot_width},
    height = {params.plot_height}
)
""")

    try:
        result = subprocess.run(
            ["Rscript", r_script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"error": "R script execution timed out"}
    finally:
        os.remove(r_script_path)