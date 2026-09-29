import argparse
import time
import ctypes

from ctypes import wintypes
from pywinauto import Desktop

TITLE_TO_READ = "Imprimir"#"Preparando relatório - Ficha_Financeira_Resumo_Geral"

def lerScreen():
    print("Procurando janelas abertas...\n")

    janelas = Desktop(backend="win32").windows()

    for i, janela in enumerate(janelas):
        try:
            print(f"[{i}] {janela.window_text()}")
        except Exception:
            pass


def lerBotoes():
    desktop = Desktop(backend="win32")

    janelas = desktop.windows(
        title=TITLE_TO_READ,
        top_level_only=True
    )

    print(f"Janelas encontradas com título {TITLE_TO_READ!r}: {len(janelas)}\n")

    for i, janela in enumerate(janelas):
        try:
            print("=" * 70)
            print(f"[{i}]")
            print("Handle :", janela.handle)
            print("Título :", repr(janela.window_text()))
            print("Classe :", repr(janela.class_name()))
            print("Rect   :", janela.rectangle())
            print("Visível:", janela.is_visible())
            print("Ativa  :", janela.is_active())
        except Exception as e:
            print(f"Erro: {e}")

def lerBotoes2():
    janela = Desktop(backend="win32").window(
        title=TITLE_TO_READ
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
        title=TITLE_TO_READ
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    controles = janela.descendants()

    print(f"Total de controles encontrados: {len(controles)}\n")

    for i, controle in enumerate(controles):
        try:
            rect = controle.rectangle()

            print(
                f"[{i}] "
                f"texto={controle.window_text()!r} | "
                f"classe={controle.class_name()!r} | "
                f"handle={controle.handle} | "
                f"posição=({rect.left}, {rect.top}) | "
                f"tamanho=({rect.width()}x{rect.height()})"
            )

        except Exception as e:
            print(f"[{i}] Erro: {e}")


def lerControlesImprimir():
    janela = Desktop(backend="win32").window(
        class_name="TfrPrintForm"
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    controles = janela.descendants()

    print(f"Total de controles encontrados: {len(controles)}\n")

    for i, controle in enumerate(controles):
        try:
            rect = controle.rectangle()

            print(
                f"[{i}] "
                f"texto={controle.window_text()!r} | "
                f"classe={controle.class_name()!r} | "
                f"handle={controle.handle} | "
                f"posição=({rect.left}, {rect.top}) | "
                f"tamanho=({rect.width()}x{rect.height()})"
            )

        except Exception as e:
            print(f"[{i}] Erro: {e}")


def diagnosticoWin32():
    janela = Desktop(backend="win32").window(
        title=TITLE_TO_READ#"FmImpSelecionaDados"
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
        title=TITLE_TO_READ#"FmImpSelecionaDados"
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
        title=TITLE_TO_READ#"FmImpSelecionaDados"
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


def lerHints():
    janela = Desktop(backend="win32").window(
        title=TITLE_TO_READ
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    from pywinauto import mouse

    controles = janela.descendants()
    desktop = Desktop(backend="win32")

    print("\nPROCURANDO HINTS...")
    print("=" * 80)

    for i, controle in enumerate(controles):

        try:
            rect = controle.rectangle()

            if rect.width() <= 0 or rect.height() <= 0:
                continue

            x = (rect.left + rect.right) // 2
            y = (rect.top + rect.bottom) // 2

            # -------------------------------------------------
            # Snapshot ANTES
            # -------------------------------------------------

            antes = {
                item.handle
                for item in desktop.windows()
            }

            # -------------------------------------------------
            # Move mouse
            # -------------------------------------------------

            mouse.move(coords=(x, y))

            time.sleep(1.0)

            # -------------------------------------------------
            # Snapshot DEPOIS
            # -------------------------------------------------

            depois = desktop.windows()

            novas = []

            for item in depois:

                try:
                    if item.handle not in antes:
                        novas.append(item)

                except Exception:
                    pass

            # -------------------------------------------------
            # Filtra somente possíveis Hints
            # -------------------------------------------------

            for item in novas:

                try:
                    titulo = item.window_text()
                    classe = item.class_name()

                    # Ignora coisas conhecidas que não interessam
                    classes_ignoradas = {
                        "IME",
                        "TDataSetValidDialog",
                    }

                    if classe in classes_ignoradas:
                        continue

                    if not titulo:
                        continue

                    print()
                    print(f"CONTROLE [{i}]")
                    print(f"  Texto       : {controle.window_text()!r}")
                    print(f"  Classe      : {controle.class_name()!r}")
                    print(f"  Handle      : {controle.handle}")
                    print(f"  HINT        : {titulo!r}")
                    print(f"  Classe Hint : {classe!r}")
                    print("-" * 80)

                except Exception:
                    pass

        except Exception:
            pass


def lerPropriedades():
    janela = Desktop(backend="win32").window(
        title=TITLE_TO_READ
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    controles = janela.descendants()

    print("\nPROPRIEDADES DOS CONTROLES")
    print("=" * 80)

    for i, controle in enumerate(controles):

        try:
            propriedades = controle.get_properties()

            textos = {}

            for nome, valor in propriedades.items():

                if valor is None:
                    continue

                valor_str = str(valor).strip()

                if not valor_str:
                    continue

                # Procuramos propriedades que possam conter
                # o texto do Hint/Gadget
                if any(
                    palavra in nome.lower()
                    for palavra in [
                        "text",
                        "name",
                        "title",
                        "caption",
                        "description",
                        "help",
                        "hint",
                    ]
                ):
                    textos[nome] = valor

            if not textos:
                continue

            print()
            print(f"CONTROLE [{i}]")
            print("-" * 80)

            print(
                "Classe :",
                repr(controle.class_name())
            )

            print(
                "Handle :",
                controle.handle
            )

            print(
                "Texto  :",
                repr(controle.window_text())
            )

            for nome, valor in textos.items():
                print(
                    f"  {nome:<20}: {valor!r}"
                )

        except Exception as e:
            print(
                f"[{i}] Erro: {e}"
            )


def lerControleMouse():
    user32 = ctypes.windll.user32

    ponto = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(ponto))

    hwnd = user32.WindowFromPoint(ponto)

    if not hwnd:
        print("Nenhum controle encontrado.")
        return

    desktop = Desktop(backend="win32")

    controle = desktop.window(handle=hwnd)

    print("POSIÇÃO DO MOUSE")
    print("-" * 50)
    print("X:", ponto.x)
    print("Y:", ponto.y)

    print("\nCONTROLE SOB O MOUSE")
    print("-" * 50)
    print("Texto  :", repr(controle.window_text()))
    print("Classe :", repr(controle.class_name()))
    print("Handle :", controle.handle)
    print("Rect   :", controle.rectangle())

    print("\nPAIS")
    print("-" * 50)

    atual = controle

    for nivel in range(10):
        try:
            pai_hwnd = user32.GetParent(atual.handle)

            if not pai_hwnd:
                break

            pai = desktop.window(handle=pai_hwnd)

            print(
                f"[{nivel + 1}] "
                f"Classe={pai.class_name()!r} | "
                f"Texto={pai.window_text()!r} | "
                f"Handle={pai.handle}"
            )

            atual = pai

        except Exception as e:
            print("Erro:", e)
            break

    print("\nFILHOS DO CONTROLE SOB O MOUSE")
    print("-" * 50)

    try:
        filhos = controle.children()

        print("Quantidade:", len(filhos))

        for i, filho in enumerate(filhos):
            print(
                f"[{i}] "
                f"Classe={filho.class_name()!r} | "
                f"Texto={filho.window_text()!r} | "
                f"Handle={filho.handle} | "
                f"Rect={filho.rectangle()}"
            )

    except Exception as e:
        print("Erro:", e)


def testarCliqueMouse():
    janela = Desktop(backend="win32").window(
        title=TITLE_TO_READ
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    print("Posicione o mouse sobre o botão 'Imprimir'.")
    input("Pressione ENTER quando estiver sobre o botão...")

    user32 = ctypes.windll.user32

    ponto = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(ponto))

    print("\nMOUSE")
    print("-" * 50)
    print("X:", ponto.x)
    print("Y:", ponto.y)

    hwnd = user32.WindowFromPoint(ponto)

    print("HWND:", hwnd)

    if hwnd:
        controle = Desktop(backend="win32").window(handle=hwnd)

        print("Classe:", repr(controle.class_name()))
        print("Texto :", repr(controle.window_text()))

    print("\nAgora pressione o botão esquerdo do mouse.")
    print("Aguardando...")

    time.sleep(1)


def monitorarMouse():
    user32 = ctypes.windll.user32

    print("Mova o mouse sobre a barra.")
    print("Pressione CTRL+C para parar.\n")

    ultima = None

    while True:
        ponto = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(ponto))

        posicao = (ponto.x, ponto.y)

        if posicao != ultima:
            hwnd = user32.WindowFromPoint(ponto)

            try:
                controle = Desktop(backend="win32").window(
                    handle=hwnd
                )

                print(
                    f"X={ponto.x:<4} "
                    f"Y={ponto.y:<4} "
                    f"HWND={hwnd:<10} "
                    f"Classe={controle.class_name()!r}"
                )

            except Exception:
                pass

            ultima = posicao

        time.sleep(0.05)


def clicarImprimir():
    janela = Desktop(backend="win32").window(
        title=TITLE_TO_READ
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    painel = janela.child_window(
        class_name="TPanel"
    )

    print("Painel encontrado:", painel.exists())
    print("Rect:", painel.rectangle())

    painel.click_input(
        coords=(315, 20)
    )

def testarPosicaoImprimir():
    janela = Desktop(backend="win32").window(
        title=TITLE_TO_READ
    )

    if not janela.exists():
        print("Janela não encontrada.")
        return

    # TPanel da barra superior
    painel = Desktop(backend="win32").window(
        handle=1575844
    )

    if not painel.exists():
        print("Painel não encontrado.")
        return

    rect = painel.rectangle()

    print("Painel encontrado:")
    print("Handle:", painel.handle)
    print("Classe:", painel.class_name())
    print("Rect:", rect)

    # Posição aproximada do gadget Imprimir
    x = rect.left + 315
    y = rect.top + 20

    print(f"\nMovendo mouse para X={x}, Y={y}")

    ctypes.windll.user32.SetCursorPos(x, y)

    print("Mouse posicionado.")
    print("Verifique se aparece o texto 'Imprimir'.")


def clicarOndeEstaOMouse():
    user32 = ctypes.windll.user32

    ponto = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(ponto))

    hwnd = user32.WindowFromPoint(ponto)

    if not hwnd:
        print("Nenhum controle encontrado.")
        return

    controle = Desktop(backend="win32").window(
        handle=hwnd
    )

    print("CONTROLE")
    print("-" * 50)
    print("X:", ponto.x)
    print("Y:", ponto.y)
    print("Classe:", controle.class_name())
    print("Texto:", repr(controle.window_text()))
    print("Handle:", controle.handle)
    print("Rect:", controle.rectangle())

    print("\nClique em 3 segundos...")

    time.sleep(3)

    user32.SetCursorPos(ponto.x, ponto.y)

    # Clique esquerdo
    user32.mouse_event(
        0x0002,  # MOUSEEVENTF_LEFTDOWN
        0,
        0,
        0,
        0
    )

    user32.mouse_event(
        0x0004,  # MOUSEEVENTF_LEFTUP
        0,
        0,
        0,
        0
    )

    print("Clique realizado.")


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

    parser.add_argument(
        "--lerControlesImprimir",
        action="store_true",
        help="Investiga o elemento ativo após cada TAB."
    )

    parser.add_argument(
        "--lerHints",
        action="store_true",
        help="Move o mouse pelos controles e procura os Hints."
    )

    parser.add_argument(
        "--lerPropriedades",
        action="store_true",
        help="Mostra propriedades textuais dos controles."
    )

    parser.add_argument(
        "--lerControleMouse",
        action="store_true",
        help="Identifica o controle que está sob o mouse."
    )

    parser.add_argument(
        "--testarCliqueMouse",
        action="store_true",
        help="Investiga o controle sob o mouse."
    )
 
    parser.add_argument(
        "--monitorarMouse",
        action="store_true",
        help="Monitora a posição do mouse."
    )

    parser.add_argument(
        "--clicarImprimir",
        action="store_true",
        help="Clica no gadget Imprimir."
    )
    
    parser.add_argument(
        "--clicarOndeEstaOMouse",
        action="store_true",
        help="Clica na posição atual do mouse."
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

    if args.lerControles:
        lerControlesImprimir()

    if args.diagnostico:
        diagnosticoWin32()

    if args.testarTeclado:
        testarTeclado()

    if args.testarFoco:
        testarFoco()    

    if args.lerHints:
        lerHints()

    if args.lerPropriedades:
        lerPropriedades()

    if args.lerControleMouse:
        lerControleMouse()

    if args.testarCliqueMouse:
        testarCliqueMouse()

    if args.monitorarMouse:
        monitorarMouse()

    if args.clicarImprimir:
        clicarImprimir()

    if args.clicarOndeEstaOMouse:
        clicarOndeEstaOMouse()
    
   
if __name__ == "__main__":
    main()


user32 = ctypes.windll.user32


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]

'''
def ler_controle_mouse():
    ponto = POINT()

    user32.GetCursorPos(ctypes.byref(ponto))

    hwnd = user32.WindowFromPoint(ponto)

    print("=" * 60)
    print("POSIÇÃO DO MOUSE")
    print("=" * 60)
    print(f"X: {ponto.x}")
    print(f"Y: {ponto.y}")

    print("\n" + "=" * 60)
    print("WINDOWFROMPOINT")
    print("=" * 60)
    print(f"HWND: {hwnd}")

    if hwnd:
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buffer, 256)

        print(f"Classe: {buffer.value}")

        buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buffer, 256)

        print(f"Texto : {buffer.value!r}")


if __name__ == "__main__":
    ler_controle_mouse()

'''