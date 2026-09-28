import argparse
import time
import ctypes

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
        title="Gerador de Relatórios ( Versão: 4.0 ) - Recursos Humanos e Folha de Pagamento"
    )

    print("Janela encontrada:", janela.exists())

    if not janela.exists():
        print("Janela não encontrada.")
        return

    print("\nINFORMAÇÕES DA JANELA")
    print("-" * 60)
    print("Handle:", janela.handle)
    print("Título:", janela.window_text())
    print("Classe:", janela.class_name())
    print("Rect:", janela.rectangle())

    print("\nCONTROLES:")
    print("-" * 60)

    janela.print_control_identifiers()

def lerBotoes2():
    janela = Desktop(backend="win32").window(
        title="Gerador de Relatórios ( Versão: 4.0 ) - Recursos Humanos e Folha de Pagamento"
    )

    print("Janela encontrada:", janela.exists())

    if not janela.exists():
        return

    print("\nCONTROLES ENCONTRADOS:\n")

    janela.print_control_identifiers(
        depth=5
    )

def lerControles():
    janela = Desktop(backend="win32").window(
        title="Gerador de Relatórios ( Versão: 4.0 ) - Recursos Humanos e Folha de Pagamento"
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    controles = janela.descendants()

    print(f"Total de controles encontrados: {len(controles)}\n")

    for i, controle in enumerate(controles):
        try:
            texto = controle.window_text()
            classe = controle.class_name()

            if texto or classe:
                print(
                    f"[{i}] "
                    f"texto={texto!r} | "
                    f"classe={classe!r} | "
                    f"handle={controle.handle}"
                )

        except Exception:
            pass
            
def diagnosticoWin32():
    janela = Desktop(backend="win32").window(
        title="FmImpSelecionaDados"
    )

    print("Janela encontrada:", janela.exists())

    if not janela.exists():
        return

    print("\nINFORMAÇÕES DA JANELA")
    print("-" * 50)
    print("Handle:", janela.handle)
    print("Título:", janela.window_text())
    print("Classe:", janela.class_name())
    print("Rect:", janela.rectangle())

    print("\nFILHOS DIRETOS")
    print("-" * 50)

    filhos = janela.children()

    print("Quantidade:", len(filhos))

    for i, filho in enumerate(filhos):
        try:
            print(
                f"[{i}] "
                f"texto={filho.window_text()!r} | "
                f"classe={filho.class_name()!r} | "
                f"handle={filho.handle}"
            )
        except Exception as e:
            print(f"[{i}] Erro: {e}")

class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("hwndActive", ctypes.c_void_p),
        ("hwndFocus", ctypes.c_void_p),
        ("hwndCapture", ctypes.c_void_p),
        ("hwndMenuOwner", ctypes.c_void_p),
        ("hwndMoveSize", ctypes.c_void_p),
        ("hwndCaret", ctypes.c_void_p),
    ]


def obter_foco():
    user32 = ctypes.windll.user32

    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(GUITHREADINFO)

    if user32.GetGUIThreadInfo(0, ctypes.byref(info)):
        return info.hwndFocus

    return None


def testarTeclado():
    janela = Desktop(backend="win32").window(
        title="FmImpSelecionaDados"
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    print("Janela encontrada.")
    print("Handle:", janela.handle)

    janela.set_focus()

    print("\nTestando navegação com TAB...\n")

    for i in range(10):
        janela.type_keys("{TAB}")

        time.sleep(0.3)

        hwnd = obter_foco()

        if hwnd:
            print(
                f"TAB {i + 1}: "
                f"HWND={hwnd}"
            )

            try:
                controle = Desktop(backend="win32").window(
                    handle=hwnd
                )

                print(
                    f"       Texto: {controle.window_text()!r}"
                )

                print(
                    f"       Classe: {controle.class_name()!r}"
                )

            except Exception as e:
                print(f"       Não foi possível identificar: {e}")

        else:
            print(
                f"TAB {i + 1}: "
                "nenhum foco identificado"
            )

def testarFoco():
    janela = Desktop(backend="win32").window(
        title="FmImpSelecionaDados"
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    janela.set_focus()

    print("Janela:", janela.window_text())
    print("Handle:", janela.handle)
    print("\nPressione TAB e analisaremos o foco.\n")

    for i in range(10):
        janela.type_keys("{TAB}")
        time.sleep(0.5)

        try:
            foco = Desktop(backend="win32").get_active()
            
            print(f"TAB {i + 1}")
            print("  Janela ativa:", foco.window_text())
            print("  Classe:", foco.class_name())
            print("  Handle:", foco.handle)

        except Exception as e:
            print(f"TAB {i + 1} - erro: {e}")

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

    parser.add_argument(
        "--lerBotoes2",
        action="store_true",
        help="Lista os controles da janela FmImpSelecionaDados."
    )

    parser.add_argument(
        "--diagnostico",
        action="store_true",
        help="Executa diagnóstico detalhado da janela."
    )

    parser.add_argument(
        "--testarTeclado",
        action="store_true",
        help="Testa navegação da janela usando teclado."
    )

    parser.add_argument(
        "--testarFoco",
        action="store_true",
        help="Investiga o elemento ativo após cada TAB."
    )

    parser.add_argument(
        "--lerControles",
        action="store_true",
        help="Investiga o elemento ativo após cada TAB."
    )

    args = parser.parse_args()

    if args.lerScreen:
        lerScreen()

    if args.lerBotoes:
        lerBotoes()

    if args.lerBotoes2:
        lerBotoes2()

    if args.lerControles:
        lerControles()

    if args.diagnostico:
        diagnosticoWin32()

    if args.testarTeclado:
        testarTeclado()

    if args.testarFoco:
        testarFoco()    

if __name__ == "__main__":
    main()