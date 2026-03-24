import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path to resolve 'src.' imports correctly for legacy code
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.iwa_rnaseq_reporter.io.read_matrix_spec import read_matrix_spec
from src.iwa_rnaseq_reporter.io.read_comparison_spec import read_comparison_spec
from src.iwa_rnaseq_reporter.io.write_result_spec import write_result_spec
from src.iwa_rnaseq_reporter.io.write_report_payload_spec import write_report_payload_spec
from src.iwa_rnaseq_reporter.io.write_execution_run_spec import write_execution_run_spec
from src.iwa_rnaseq_reporter.pipeline.runner import run_reporter_pipeline

def main():
    parser = argparse.ArgumentParser(description="iwa_rnaseq_reporter CLI")
    parser.add_argument("--matrix-spec", required=True, type=Path)
    parser.add_argument("--comparison-spec", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--run-id", type=str)
    parser.add_argument("--profile", type=str, default="default")
    parser.add_argument("--analysis-mode", type=str, default="preview")
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-plots", action="store_true")
    parser.add_argument("--skip-enrichment", action="store_true")
    parser.add_argument("--log-level", type=str, default="INFO")

    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    logging.basicConfig(level=numeric_level, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    try:
        matrix_spec = read_matrix_spec(args.matrix_spec)
        comparison_spec = read_comparison_spec(args.comparison_spec)
    except Exception as e:
        logger.error(f"Failed to read specs: {e}")
        sys.exit(1)

    if args.dry_run:
        logger.info("Dry run complete. Specs parsed successfully.")
        return

    logger.info("Starting reporter pipeline")
    try:
        res_spec, rp_spec, run_spec = run_reporter_pipeline(
            matrix_spec, 
            comparison_spec, 
            args.outdir,
            dry_run=args.dry_run
        )
        
        write_result_spec(res_spec, args.outdir / "specs" / "result.spec.json")
        write_report_payload_spec(rp_spec, args.outdir / "specs" / "report-payload.spec.json")
        write_execution_run_spec(run_spec, args.outdir / "specs" / "execution-run.spec.json")
        
        logger.info("Pipeline completed perfectly. Outputs written to specs/")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
