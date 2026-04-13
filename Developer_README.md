# iwa-rnaseq-reporter: Developer Documentation

## Responsibility & Boundary

### Core Responsibility
The `iwa-rnaseq-reporter` is an **analytics and reporting hub** designed to interpret standardized RNA-Seq quantification data.

### In Scope
- Statistical analysis of differential expression (DEG).
- Exploratory visualization (PCA, heatmaps) and functional analysis (Enrichment).
- Narrative and structured research report generation (HTML, PDF, Handoff Bundles).

### Out of Scope
- Direct processing of raw FASTQ files or execution of quantifiers (STAR, Salmon, etc.).
- Direct parsing of varied vendor delivery formats (delegated to the Adapter layer).

### Architectural Constraints
- **Standardized Ingestion Only**: The core engine must only consume data via standardized contracts (`MatrixSpec`, `ComparisonSpec`).
- **Adapter Isolation**: All vendor-specific logic must be isolated in the Adapter layer to prevent core engine pollution.

For the full suite architecture and layer definitions, see: [RNA-Seq Suite App Boundary](../dev_docs/rnaseq-suite-app-boundary.md).
