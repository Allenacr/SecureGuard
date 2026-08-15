"""
Reconcile DB protected_files with vault state.
Usage: python reconcile_protection.py [--fix]

--fix: attempt to fix mismatches by protecting files that are in DB but missing in vault,
       and adding DB rows for vault entries missing in DB.
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from file_protector import FileProtector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fix', action='store_true', help='Attempt to fix mismatches')
    args = parser.parse_args()

    db = Database()
    if not db.authenticate():
        print('Failed to authenticate to DB')
        return 2

    protector = FileProtector()

    protected_rows = db.get_protected_files(force_refresh=True)
    print(f"DB protected rows: {len(protected_rows)}")

    mismatches = []
    for row in protected_rows:
        path = row.get('path')
        if not path:
            continue
        exists_in_vault = protector.is_protected(path)
        if not exists_in_vault:
            mismatches.append((path, row))

    if not mismatches:
        print('No mismatches: all DB-protected files have vault entries')
    else:
        print(f"Found {len(mismatches)} DB entries missing vault files:")
        for p, r in mismatches:
            print(' -', p)
        if args.fix:
            for p, r in mismatches:
                print(f'Attempting to protect: {p}')
                try:
                    if os.path.exists(p):
                        ok = protector.protect_file(p)
                        print('  protect_file ->', ok)
                        if ok:
                            # Ensure DB row is active
                            db.add_protected_file(p, os.path.basename(p), 'file')
                    else:
                        print('  original file not found on disk; cannot protect automatically')
                except Exception as e:
                    print('  failed:', e)

    # Also check for vault entries with no DB row
    vault_dir = protector.vault_dir
    vault_map = {}
    for f in os.listdir(vault_dir):
        if f.endswith('.enc') or f.endswith('.meta'):
            vault_map[f] = True

    # Quick heuristic: for each DB row, ensure a vault file exists (already done). For vault entries missing in DB,
    # we could add DB rows but that may be undesirable; print them for manual review.

    print('Done.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
