#!/usr/bin/env python
"""Executa comandos administrativos do projeto Django."""

import os
import sys


def main() -> None:
    """Configura o ambiente e delega a execucao ao Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.desenvolvimento")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
