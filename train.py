import sys

from oil_uplift.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["train", *sys.argv[1:]]))
