#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 4) {
  stop("Usage: Rscript run_ridgeplot.R <input_file> <output_dir> <width> <height>")
}

input_file <- args[1]
output_dir <- args[2]
width <- as.numeric(args[3])
height <- as.numeric(args[4])

library(limma)
library(clusterProfiler)
library(org.Hs.eg.db)
library(enrichplot)
library(ggplot2)

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

df <- read.csv(input_file, check.names = FALSE, stringsAsFactors = FALSE)
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
saveRDS(rank_list, file = file.path(output_dir, "rank_list.rds"))
saveRDS(geneList,  file.path(output_dir, "geneList_t.rds"))

for (ont in c("BP","CC","MF")) {
  gse <- gseGO(geneList = geneList, OrgDb = org.Hs.eg.db, keyType = "SYMBOL",
               ont = ont, minGSSize = 10, maxGSSize = 500,
               pvalueCutoff = 0.05, pAdjustMethod = "BH", verbose = FALSE)
  saveRDS(gse, file = file.path(output_dir, paste0("gse_", ont, ".rds")))
  if (is.null(gse) || nrow(gse@result) == 0) next
  p <- ridgeplot(gse, showCategory = 20, fill = "p.adjust", label_format = 40) +
       labs(title = paste("GSEA Ridgeplot (GO:", ont, ")"),
            x = "enrichment distribution") +
       theme_bw()
  ggsave(file.path(output_dir, paste0("ridgeplot_", ont, ".svg")),
         p, width = width, height = height, device = "svg")
}