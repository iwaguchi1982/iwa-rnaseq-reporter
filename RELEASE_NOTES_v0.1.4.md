# iwa-rnaseq-reporter v0.1.4

## Overview

`v0.1.4` formalizes the dependency between the Analysis Matrix setup and the DEG Comparison Design, ensuring strict data consistency throughout the exploratory workflow.

## Added & Improved

- **Strict Analysis-Sample Dependency**
  - Comparison candidate columns are now filtered based on the *currently included* analysis samples only.
  - Group summaries now reflect the active analysis subset.
- **UI Settings Transparency**
  - Section 13 now explicitly displays the active Analysis Matrix settings (kind, log-transform, etc.) applied to the comparison.
- **Enhanced DEGInput Layer**
  - Guaranteed alignment between `feature_matrix` columns and `sample_table` rows.
  - Automatic exclusion of empty/whitespace-only metadata groups.

## Fixed

- Corrected a potential mismatch between the metadata display and the actual samples used in the DEG Preview.
- Improved validation messages when group sizes are insufficient for comparison.

## Positioning

This release solidifies `iwa-rnaseq-reporter` as a consistent exploratory tool where downstream steps (PCA, Correlation, DEG Preview) are strictly derived from the user-defined Analysis Setup.
