import argparse

from pywinauto import Desktop


def lerScreen():
    print("Procurando janelas abertas...\n")

    janelas = Desktop(backend="win32").windows()

    for i, janela in enumerate(janelas):
        try:
            print(f"[{i}] {janela.window_text()}")
        except Exception:
            pass


def lerBotoes():
    janela = Desktop(backend="win32").window(
        title="FmImpSelecionaDados"
    )

    print("Janela encontrada:", janela.exists())
    print("\nCONTROLES:\n")

    janela.print_control_identifiers()


def main():
    parser = argparse.ArgumentParser(
        description="Auxiliar para interação com a interface do sistema."
    )

    parser.add_argument(
        "--lerScreen",
        action="store_true",
        help="Lista as janelas abertas no Windows."
    )

    parser.add_argument(
        "--lerBotoes",
        action="store_true",
        help="Lista os controles da janela FmImpSelecionaDados."
    )

    args = parser.parse_args()

    if args.lerScreen:
        lerScreen()

    if args.lerBotoes:
        lerBotoes()


if __name__ == "__main__":
    main()