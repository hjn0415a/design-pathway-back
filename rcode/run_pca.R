
# --- 라이브러리 로드 ---
suppressPackageStartupMessages({
  library(readr)
  library(factoextra)
  library(ggrepel)
  library(svglite)
})

# --- 명령줄 인자 받기 ---
args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 7) {
  stop("Usage: Rscript run_pca.R <csv_path> <width> <height> <pointshape> <pointsize> <text_size> <output_svg>")
}

csv_path   <- args[1]
width      <- as.numeric(args[2])
height     <- as.numeric(args[3])
pointshape <- as.numeric(args[4])
pointsize  <- as.numeric(args[5])
text_size  <- as.numeric(args[6])
output_svg <- args[7]

# --- 데이터 로드 ---
dat <- as.data.frame(read_csv(csv_path))

# 샘플 열 추출 (Geneid, foldchange, pvalue 제외)
sample_cols <- grep("(^Group)|(_[0-9]+$)", names(dat), value = TRUE)
X <- t(as.matrix(dat[, sample_cols, drop = FALSE]))
rownames(X) <- sample_cols

# NA 제거 후 표준화
Xz <- scale(X, center = TRUE, scale = TRUE)
Xz <- Xz[, colSums(is.na(Xz)) == 0, drop = FALSE]

# --- PCA 계산 ---
pca_res <- prcomp(Xz, center = FALSE, scale. = FALSE)
rownames(pca_res$x) <- rownames(X)
sample_groups <- factor(sub("(_[0-9]+$)|([0-9]+$)", "", rownames(pca_res$x)))

df <- data.frame(
  PC1 = pca_res$x[,1],
  PC2 = pca_res$x[,2],
  sample = rownames(pca_res$x),
  group = sample_groups
)

# --- SVG 파일 생성 ---
svglite(output_svg, width = width, height = height)

p <- fviz_pca_ind(
  pca_res,
  geom.ind   = "point",
  col.ind    = sample_groups,
  pointshape = pointshape,
  pointsize  = pointsize,
  mean.point = FALSE,
  addEllipses= FALSE
) +
  geom_text_repel(
    data = df,
    aes(PC1, PC2, label = sample, color = group),
    size = text_size,
    show.legend = FALSE
  )

print(p)
dev.off()