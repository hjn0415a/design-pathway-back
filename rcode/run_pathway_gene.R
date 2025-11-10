# Usage:
# Rscript run_pathway_gene.R csv_path edox_dir output_dir top_pathways top_genes width height max_setsize

args <- commandArgs(trailingOnly=TRUE)
csv_path <- args[1]
edox_dir <- args[2]
output_dir <- args[3]
top_pathways <- as.numeric(args[4])
top_genes <- as.numeric(args[5])
width <- as.numeric(args[6])
height <- as.numeric(args[7])
max_setsize <- as.numeric(args[8])

library(clusterProfiler)
library(enrichplot)
library(ggplot2)
library(cowplot)
library(org.Hs.eg.db)

df <- read.csv(csv_path, check.names=FALSE, stringsAsFactors=FALSE)
stopifnot("Geneid" %in% names(df), "foldchange" %in% names(df))
fc_vec <- setNames(log2(df$foldchange + 1e-8), df$Geneid)
fc_vec <- fc_vec[is.finite(fc_vec)]

harmonize_fc <- function(edox, fc_named) {
  core_ids <- unique(unlist(strsplit(edox@result$core_enrichment, "/")))
  if(length(core_ids) == 0 || all(is.na(core_ids))) return(fc_named)
  if(sum(names(fc_named) %in% core_ids) > 0) return(fc_named)
  is_entrez <- all(grepl("^[0-9]+$", head(core_ids[!is.na(core_ids)], 50)))
  if(is_entrez) {
    mp <- suppressMessages(bitr(names(fc_named), fromType="SYMBOL", toType="ENTREZID", OrgDb=org.Hs.eg.db))
    if(!nrow(mp)) return(numeric(0))
    mp <- mp[!duplicated(mp$SYMBOL), ]
    out <- fc_named[mp$SYMBOL]; names(out) <- mp$ENTREZID
    out[!is.na(names(out))]
  } else {
    mp <- suppressMessages(bitr(names(fc_named), fromType="ENTREZID", toType="SYMBOL", OrgDb=org.Hs.eg.db))
    if(!nrow(mp)) return(numeric(0))
    mp <- mp[!duplicated(mp$ENTREZID), ]
    out <- fc_named[mp$ENTREZID]; names(out) <- mp$SYMBOL
    out[!is.na(names(out))]
  }
}

files <- c(BP="gse_BP.rds", CC="gse_CC.rds", MF="gse_MF.rds")

for(ont in names(files)) {
  rds <- file.path(edox_dir, files[ont])
  if(!file.exists(rds)) next
  edox <- try(readRDS(rds), silent=TRUE)
  if(inherits(edox, "try-error") || nrow(edox@result) == 0) next
  if(!is.null(max_setsize) && "setSize" %in% names(edox@result)) {
    edox@result <- edox@result[edox@result$setSize <= max_setsize, , drop=FALSE]
    if(nrow(edox@result)==0) next
  }
  fc_use <- harmonize_fc(edox, fc_vec)
  if(!length(fc_use)) next
  fc_use <- fc_use[is.finite(fc_use)]
  res_top <- head(edox@result[order(edox@result$p.adjust), , drop=FALSE], top_pathways)
  core_top <- unique(unlist(strsplit(res_top$core_enrichment, "/")))
  fc_use <- fc_use[names(fc_use) %in% core_top]
  fc_use <- fc_use[order(abs(fc_use), decreasing=TRUE)]
  fc_use <- head(fc_use, top_genes)

  p1 <- heatplot(edox, showCategory=top_pathways) + theme(axis.text.x=element_text(angle=45,hjust=1,size=7))
  p2 <- heatplot(edox, foldChange=fc_use, showCategory=top_pathways) + theme(axis.text.x=element_text(angle=45,hjust=1,size=7))

  g <- cowplot::plot_grid(p1, p2, ncol=1, labels=c("A","B"))
  ggsave(file.path(output_dir, sprintf("heatplot_%s_top%dgenes.svg", ont, top_genes)), g, width=width, height=height)
}