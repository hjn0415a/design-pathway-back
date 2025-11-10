# Usage:
# Rscript run_gseaplot_total.R input_dir output_dir topN width height

args <- commandArgs(trailingOnly=TRUE)
input_dir <- args[1]
output_dir <- args[2]
topN <- as.numeric(args[3])
width <- as.numeric(args[4])
height <- as.numeric(args[5])

library(clusterProfiler)
library(enrichplot)
library(ggplot2)

ont_files <- c(BP = "gse_BP.rds", CC = "gse_CC.rds", MF = "gse_MF.rds")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

for (ont in names(ont_files)) {
  rds_path <- file.path(input_dir, ont_files[[ont]])
  if (!file.exists(rds_path)) next

  gse <- try(readRDS(rds_path), silent=TRUE)
  if (inherits(gse, "try-error") || !inherits(gse, "gseaResult")) next
  if (is.null(gse@result) || nrow(gse@result) == 0) next

  res <- as.data.frame(gse@result)
  res[] <- lapply(res, function(x) if (inherits(x, "Rle")) as.vector(x) else x)
  if (!all(c("ID","p.adjust") %in% names(res))) next
  res$p.adjust <- suppressWarnings(as.numeric(res$p.adjust))
  ord <- order(res$p.adjust, na.last = NA)
  if (!length(ord)) next
  sel <- ord[ seq_len(min(topN, length(ord))) ]
  ids <- res$ID[sel]

  p <- gseaplot2(gse, geneSetID=ids, pvalue_table=TRUE,
                 title=sprintf("Top %d enriched GO:%s terms", length(ids), ont))
  ggsave(file.path(output_dir, sprintf("gseaplot2_%s_top%d.svg", ont, length(ids))),
         plot=p, width=width, height=height)
}