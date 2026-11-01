"""Create single-use InternPilot AI invitation codes.

Run from the backend directory:
    python -m app.create_invite --count 5
    python -m app.create_invite --count 1 --note "early access invite"
"""
import argparse
import hashlib
import secrets

from .db import connect, init_db

def make_code():
    raw = secrets.token_hex(6).upper()
    return "IP-" + "-".join(raw[i:i+4] for i in range(0, 12, 4))

def main():
    parser = argparse.ArgumentParser(description="Create single-use InternPilot AI invite codes.")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    if args.count < 1 or args.count > 100:
        parser.error("--count must be between 1 and 100")
    init_db()
    codes = []
    with connect() as db:
        for _ in range(args.count):
            code = make_code()
            digest = hashlib.sha256(code.replace("-", "").encode("utf-8")).hexdigest()
            db.execute("INSERT INTO invite_codes(code_hash,note) VALUES(?,?)", (digest, args.note[:200]))
            codes.append(code)
    print("\nGive each code to one person. Each code works for one registration only.\n")
    for code in codes:
        print(code)
    print("\nThese codes are not shown again. Save or distribute them securely.\n")

if __name__ == "__main__":
    main()
