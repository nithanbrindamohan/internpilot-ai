"""Run a one-time health check against configured employer job boards.

Usage from backend/: python -m app.check_sources
Optional: python -m app.check_sources --company Waabi
"""
import argparse
from .sources import BOARDS, _fetch_one


def main():
    parser = argparse.ArgumentParser(description="Check configured public employer job feeds")
    parser.add_argument("--company", help="Only check a company (case-insensitive substring)")
    parser.add_argument("--limit", type=int, default=0, help="Check only the first N matching boards")
    args = parser.parse_args()
    boards = BOARDS
    if args.company:
        needle = args.company.casefold()
        boards = [b for b in boards if needle in b["company"].casefold()]
    if args.limit:
        boards = boards[:max(0, args.limit)]
    if not boards:
        print("No matching source boards found.")
        return 2
    ok = failed = total_jobs = 0
    for board in boards:
        jobs, status = _fetch_one(board)
        if status["success"]:
            ok += 1
            total_jobs += len(jobs)
            print(f"OK      {board['company']:<25} {board['kind']:<10} {len(jobs):>4} postings")
        else:
            failed += 1
            print(f"FAILED  {board['company']:<25} {board['kind']:<10} {status['error']}")
    print(f"\nSummary: {ok} healthy, {failed} failed, {total_jobs} postings across {len(boards)} checked boards.")
    print("A healthy board may currently have zero open postings. Recheck failures later; ATS endpoints can change.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
