from db_parallel.db_to_trello_data import build_latest_trello_like_data
from generate_completed_html import analyze_completed_projects, generate_completed_html_report


def main() -> None:
    data = build_latest_trello_like_data(db_path="db_parallel/data/trello_history.sqlite")
    projects = analyze_completed_projects(data)
    out = generate_completed_html_report(projects, output_file="db_parallel/reports/completed_projects_report.html")
    print(f"Completed projects report (DB) generated: {out}")


if __name__ == "__main__":
    main()
