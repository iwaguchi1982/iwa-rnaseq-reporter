# iwa-rnaseq-reporter v0.1.3

## Overview

`v0.1.3` extends the reporter from dataset loading and validation to exploratory analysis and comparison scaffolding.

## Added

- analysis matrix setup
  - matrix kind selection
  - `exclude` handling
  - `log2(x+1)` option
  - feature filtering (`min nonzero samples`, `min feature mean`)
- PCA preview
- sample correlation preview
- gene / feature search
- top variable features table
- DEG comparison design scaffold
- DEG preview table scaffold

## Notes

- `DEG Preview Table` is a preview layer only
- statistical testing (`p-value`, `adjusted p-value`) is not implemented yet
- comparison design requires comparison-ready metadata columns such as `group` or `condition`

## Positioning

This release establishes `iwa-rnaseq-reporter` as:

- contract reader
- dataset validator
- exploratory analysis UI
- comparison design scaffold