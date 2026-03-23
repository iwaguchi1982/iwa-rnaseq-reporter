# iwa-rnaseq-reporter v0.1.5

## Overview

`v0.1.5` is a stabilization and refinement release focused on the exploratory comparison layer. It improves consistency between comparison design, DEG input assembly, and the DEG Preview table, while also adding usability enhancements such as ranking and direction labels.

## Added & Improved

- **Refined DEG Preview Table**
  - Added a `rank` column based on absolute log2 fold change (`abs_log2_fc`).
  - Added a `direction` column (`Up` / `Down`) for easier interpretation.
  - DEG Preview results are now easier to scan for large-magnitude changes.

- **Improved Comparison Design**
  - Strengthened alignment between the comparison sample table and the backend feature matrix.
  - Refined candidate column filtering to exclude non-informative all-unique ID-like columns.
  - Improved consistency of comparison setup against the current analysis sample set.

- **Internal Architecture Refactoring**
  - Moved comparison-related UI logic into dedicated helper functions in `src/deg_input.py`.
  - Improved validation for comparison requests.
  - Reduced UI-layer complexity and improved maintainability and testability.

- **Comprehensive Testing**
  - Added 8 new test cases covering:
    - comparison sample alignment
    - sample ordering consistency
    - exclude handling
    - invalid comparison setup edge cases

## Positioning

This release marks the completion of the exploratory preview milestone. The application now has a more robust foundation for the upcoming statistical DEG testing milestone planned for `v0.2.0`.