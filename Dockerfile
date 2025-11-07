# Base Ubuntu + Bioconductor
FROM bioconductor/bioconductor_docker:RELEASE_3_21

ARG DEBIAN_FRONTEND=noninteractive

# Install Python and essential packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv curl git build-essential \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Python dependencies
COPY requirements_fastapi.txt /app/requirements_fastapi.txt
RUN pip install --no-cache-dir -r /app/requirements_fastapi.txt

# Copy FastAPI code
WORKDIR /app
COPY . /app/

# Install R packages required for heatmap & omics
RUN Rscript -e "if(!requireNamespace('BiocManager', quietly=TRUE)) install.packages('BiocManager', repos='https://cran.r-project.org')" && \
    Rscript -e "BiocManager::install(c('pheatmap','EnhancedVolcano','clusterProfiler','org.Hs.eg.db','org.Mm.eg.db','enrichplot','limma','pathview','RCy3'), update=TRUE, ask=FALSE, dependencies=TRUE)" && \
    Rscript -e "install.packages(c('svglite','ggplot2','readr','cowplot','dplyr', 'factoextra', 'ggrepel'), repos='https://cran.r-project.org')"

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]