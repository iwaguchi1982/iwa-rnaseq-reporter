import json
from pathlib import Path
from ..models.report_payload import ReportPayloadSpec

def write_report_payload_spec(spec: ReportPayloadSpec, out_path: str | Path) -> None:
    path_obj = Path(out_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(spec.to_dict(), f, indent=2, ensure_ascii=False)
