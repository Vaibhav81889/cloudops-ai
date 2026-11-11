import db


def main() -> None:
    db.init_db()
    rows = db.get_recent_checks(10)
    if not rows:
        print("No checks stored yet.")
        return
    for r in rows:
        print(
            f"{r['checked_at']}  {r['status']:<4}  {r['url']}  "
            f"code={r['status_code']}  time={r['response_time']}  error={r['error']}"
        )


if __name__ == "__main__":
    main()
