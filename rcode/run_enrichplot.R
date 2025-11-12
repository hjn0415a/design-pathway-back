# backend/rcode/run_enrichplot.R
args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 7) {
  stop("Usage: Rscript run_enrichplot.R <result_root> <output_root> <org_db> <showCategory> <pvalueCutoff> <plot_width> <plot_height>")
}

result_root  <- args[1]
output_root  <- args[2]
org_db       <- args[3]
showCategory <- as.numeric(args[4])
p_cut        <- as.numeric(args[5])
width        <- as.numeric(args[6])
height       <- as.numeric(args[7])

suppressPackageStartupMessages({
  library(clusterProfiler)
  library(enrichplot)
  library(ggplot2)
  library(DOSE)
  library(org_db, character.only = TRUE)
})

run_enrich_genedi_min <- function(result_root,
                                  output_root,
                                  combo_names,
                                  file_name    = "filtered_gene_list.csv",
                                  showCategory = 10,
                                  p_cut        = 0.05,
                                  save_ego     = TRUE,
                                  width        = 8,
                                  height       = 6) {

  for (nm in combo_names) {
    combo_dir_in <- file.path(result_root, nm)
    f <- file.path(combo_dir_in, file_name)
    if (!file.exists(f)) next

    df <- read.csv(f, check.names = FALSE, stringsAsFactors = FALSE)
    sym_col <- grep("^(Geneid|Gene_Symbol|SYMBOL)$", names(df),
                    ignore.case = TRUE, value = TRUE)[1]
    if (is.na(sym_col)) next

    conv <- tryCatch(
      bitr(df[[sym_col]], fromType = "SYMBOL", toType = "ENTREZID",
           OrgDb = get(org_db)),
      error = function(e) { NULL }
    )
    if (is.null(conv) || !"ENTREZID" %in% names(conv)) next

    ids <- unique(na.omit(conv$ENTREZID))
    if (!length(ids)) next

    combo_dir_out <- file.path(output_root, nm)
    fig_dir <- file.path(combo_dir_out, "figure")
    if (!dir.exists(fig_dir)) dir.create(fig_dir, recursive = TRUE)

    for (ont in c("BP", "CC", "MF")) {
      ego <- suppressMessages(
        enrichGO(
          gene           = ids,
          OrgDb          = get(org_db),
          keyType        = "ENTREZID",
          ont            = ont,
          pAdjustMethod  = "BH",
          pvalueCutoff   = p_cut,
          qvalueCutoff   = 1,
          readable       = TRUE
        )
      )

      if (!is.null(ego) && !is.null(ego@result) && nrow(ego@result) > 0) {
        write.csv(ego@result,
                  file.path(combo_dir_out, sprintf("GO_%s_result.csv", ont)),
                  row.names = FALSE)
        p <- dotplot(ego, showCategory = showCategory,
                     x = "GeneRatio", color = "p.adjust") +
             ggtitle(sprintf("GO %s - %s", ont, nm))
        ggsave(file.path(fig_dir, sprintf("GO_%s.svg", ont)),
               p, width = width, height = height)
        if (isTRUE(save_ego)) {
          saveRDS(ego, file.path(combo_dir_out, sprintf("GO_%s_ego.rds", ont)))
        }
      }
    }
  }
}

combo_csv_path <- file.path(result_root, "combo_names.csv")

if (!file.exists(combo_csv_path)) {
  stop(paste("Combo CSV file not found:", combo_csv_path))
}

combo_names <- read.csv(combo_csv_path, stringsAsFactors = FALSE)[["combo"]]

run_enrich_genedi_min(
  result_root = result_root,
  output_root = output_root,
  combo_names = combo_names,
  showCategory = showCategory,
  p_cut = p_cut,
  width = width,
  height = height
)

message("✅ Enrichment analysis completed successfully.")