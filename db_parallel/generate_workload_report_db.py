from db_parallel.db_to_trello_data import build_latest_trello_like_data
from generate_html_report import analyze_speaker_data, generate_html_report


def main() -> None:
    data = build_latest_trello_like_data(db_path="db_parallel/data/trello_history.sqlite")
    speaker_data = analyze_speaker_data(data)
    out = generate_html_report(speaker_data, output_file="db_parallel/reports/speaker_workload_report.html")
    print(f"Workload report (DB) generated: {out}")


if __name__ == "__main__":
    main()
