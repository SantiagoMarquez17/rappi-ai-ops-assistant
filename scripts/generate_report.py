import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import OUTPUTS_DIR  # noqa: E402
from src.insights import generate_insights, generate_markdown_report  # noqa: E402


def main() -> None:
    sections = generate_insights()
    report = generate_markdown_report(sections)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUTS_DIR / "executive_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"Executive report saved to: {report_path}")


if __name__ == "__main__":
    main()
