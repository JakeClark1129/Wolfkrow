#!/usr/bin/env python
"""
Prints a JSON description of every Task type available to Wolfkrow. (Including
custom Tasks found via WOLFKROW_TASK_SEARCH_PATHS)

This is the contract between Wolfkrow and external tools such as the Wolfkrow
Editor.
"""
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(prog="wolfkrow_describe_tasks")
    parser.add_argument("--task", action="append", help="Only describe these Task types.")
    parser.add_argument("--include-abstract", action="store_true",
        help="Include base Task types which are not intended to be used directly.")
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args()

    from wolfkrow.core.tasks import describe_all_tasks
    descriptions = describe_all_tasks(include_abstract=args.include_abstract)
    if args.task:
        descriptions = {name: descriptions[name] for name in args.task if name in descriptions}

    json.dump(descriptions, sys.stdout, indent=args.indent)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
