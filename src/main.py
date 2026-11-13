"""Ponto de entrada da CLI: ``python main.py GRUPO AÇÃO [opções]``."""

import sys

from auxiliar_interface.cli import main

if __name__ == "__main__":
    sys.exit(main())
