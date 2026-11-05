import argparse
import time
import ctypes

from ctypes import wintypes
from pywinauto import Desktop

#TITLE_TO_READ = "Salvar Saída de Impressão como"

#TITLE_TO_READ = "Preparando relatório - Ficha_Financeira_Resumo_Geral"

#TITLE_TO_READ = "Gerador de Relatórios ( Versão: 4.0 ) - Recursos Humanos e Folha de Pagamento"

#TITLE_TO_READ = "Folha - PREFEITURA MUNICIPAL DE TRES CORACOES - Abril de 2009"#"Form1"

#TITLE_TO_READ = "Confirmar Salvar como"

TITLE_TO_READ = "Menu: Arquivos / Cadastro de Funcionários"

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


def lerNome():
    desktop = Desktop(backend="win32")

    janela = desktop.window(
        title=TITLE_TO_READ
    )

    if not janela.exists(timeout=2):
        print("Janela principal não encontrada.")
        return

    print("Janela principal encontrada.")
    print()
    print("TEXTOS DOS CONTROLES")
    print("=" * 80)

    controles = janela.descendants()

    for i, controle in enumerate(controles):
        try:
            texto = controle.window_text()

            if not texto:
                continue

            print(
                f"[{i}] "
                f"texto={texto!r} | "
                f"classe={controle.class_name()!r} | "
                f"handle={controle.handle}"
            )

        except Exception:
            pass


def lerPropriedadesNome():
    desktop = Desktop(backend="win32")

    janela = desktop.window(
        title=TITLE_TO_READ
    )

    if not janela.exists(timeout=2):
        print("Janela principal não encontrada.")
        return

    print("Janela principal encontrada.")
    print()
    print("CONTROLES RELACIONADOS AO FUNCIONÁRIO")
    print("=" * 80)

    controles = janela.descendants()

    for i, controle in enumerate(controles):
        try:
            classe = controle.class_name()

            if classe not in (
                "TcxCustomInnerTextEdit",
                "TcxSpinEdit",
                "TelLookupCombo",
                "TelComboBox",
                "TComboBox",
            ):
                continue

            print("-" * 80)
            print(f"[{i}]")
            print("Classe       :", classe)
            print("Handle       :", controle.handle)
            print("Window text  :", repr(controle.window_text()))

            try:
                print("Texto        :", repr(controle.texts()))
            except Exception as e:
                print("Texto        :", f"erro: {e}")

            try:
                print("Valor        :", repr(controle.get_value()))
            except Exception as e:
                print("Valor        :", f"erro: {e}")

            try:
                print("Rect         :", controle.rectangle())
            except Exception as e:
                print("Rect         :", f"erro: {e}")

        except Exception as e:
            print(f"Erro no controle [{i}]: {e}")


def ler_textos_preview():
    desktop = Desktop(backend="win32")

    print("Procurando preview...")

    janelas = desktop.windows()

    for janela in janelas:
        try:
            titulo = janela.window_text()
            classe = janela.class_name()

            print(
                f"Janela: {titulo!r} | "
                f"Classe: {classe!r} | "
                f"Handle: {janela.handle}"
            )

            if (
                classe == "TfrmPreview"
                and titulo == "Ficha_Financeira_Resumo_Geral"
            ):
                print()
                print("Preview encontrado.")
                print()
                print("TEXTOS DO PREVIEW")
                print("=" * 80)

                for i, controle in enumerate(
                    janela.descendants()
                ):
                    try:
                        texto = controle.window_text()

                        if texto:
                            print(
                                f"[{i}] "
                                f"texto={texto!r} | "
                                f"classe={controle.class_name()!r} | "
                                f"handle={controle.handle}"
                            )

                    except Exception:
                        pass

                return

        except Exception:
            pass

    print()
    print("Preview não encontrado.")


def investigar_funcionario():
    desktop = Desktop(backend="win32")

    janela = desktop.window(
        title=TITLE_TO_READ
    )

    if not janela.exists(timeout=2):
        print("Janela principal não encontrada.")
        return

    controles = janela.descendants(
        class_name="TelLookupCombo"
    )

    print("TelLookupCombos encontrados:")
    print("=" * 70)

    for i, controle in enumerate(controles):
        try:
            print(f"\n[{i}]")
            print("Handle      :", controle.handle)
            print("Window text :", repr(controle.window_text()))
            print("Texts       :", repr(controle.texts()))
            print("Rect        :", controle.rectangle())

        except Exception as e:
            print("Erro:", e)


def ler_lista_funcionario():
    desktop = Desktop(backend="win32")

    janela = desktop.window(title=TITLE_TO_READ)

    if not janela.exists(timeout=2):
        print("Janela principal não encontrada.")
        return

    listbox = janela.window(handle=133792)

    print("LISTBOX")
    print("=" * 70)
    print("Handle :", listbox.handle)
    print("Classe :", listbox.class_name())
    print("Texto  :", repr(listbox.window_text()))

    try:
        itens = listbox.texts()

        print()
        print("ITENS")
        print("=" * 70)
        print("Quantidade:", len(itens))

        for i, item in enumerate(itens):
            print(f"[{i}] {item!r}")

    except Exception as e:
        print("Erro ao obter itens:", e)


import ctypes
from ctypes import wintypes

from pywinauto import Desktop

# --- Windows API (declarada uma única vez, com assinaturas corretas p/ 64 bits) ---
_user32 = ctypes.WinDLL("user32", use_last_error=True)

_user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetWindow.restype = wintypes.HWND
_user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetAncestor.restype = wintypes.HWND
_user32.GetDesktopWindow.argtypes = []
_user32.GetDesktopWindow.restype = wintypes.HWND

_GW_OWNER = 4
_GA_PARENT = 1


def listarJanelas():
    import ctypes
    from ctypes import wintypes
    from pywinauto import Desktop

    ignorar = {
        "lidDialog",
        "DataSetValidDialog",
        "Chart editor",
        "Editor de Cross-tab",
        "Dictionary editor",
        "Rich Edit",
        "Task Host Window",
        "CDA Server",
        "RadeonSoftware",
        "WUIconWindow",
        "OneDrive",
        "ad_msg_wnd",
        "Window",
        "Program Manager",
        "Default IME",
        "M",
    }

    # --- Windows API (assinaturas corretas, inclusive em 64 bits) ---
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetDesktopWindow.argtypes = []
    user32.GetDesktopWindow.restype = wintypes.HWND

    GW_OWNER = 4
    GA_PARENT = 1
    desktop_hwnd = user32.GetDesktopWindow()

    # 1) Descoberta + filtros originais + coleta de HWND
    nos = {}     # hwnd -> {"titulo": str, "filhos": [hwnd, ...]}
    ordem = []   # preserva a ordem de enumeração

    for janela in Desktop(backend="win32").windows():
        try:
            titulo = janela.window_text().strip()

            if not titulo:
                continue

            if titulo in ignorar:
                continue

            if "GDI+ Window" in titulo:
                continue

            if "cmd.exe" in titulo.lower():
                continue

            if "C:\\Windows" in titulo:
                continue

            if "AMD" in titulo:
                continue

            if "Microsoft" in titulo:
                continue

            if "Realtek" in titulo:
                continue

            if "Bluetooth" in titulo:
                continue

            if "HiddenFax" in titulo:
                continue

            if ".NET-BroadcastEventWindow" in titulo:
                continue

            hwnd = janela.handle
            if hwnd in nos:  # cada janela aparece uma única vez
                continue

            nos[hwnd] = {"titulo": titulo, "filhos": []}
            ordem.append(hwnd)

        except Exception:
            pass

    # 2) Relação direta: filha real (GA_PARENT) tem prioridade; depois proprietária (GW_OWNER)
    def pai_direto(hwnd):
        pai = user32.GetAncestor(hwnd, GA_PARENT)
        if pai and pai != desktop_hwnd:
            return pai
        return user32.GetWindow(hwnd, GW_OWNER) or None

    # 3) Sobe a cadeia até achar um ancestral que esteja entre as janelas exibidas
    def resolver_pai(hwnd):
        visitados = {hwnd}
        candidato = pai_direto(hwnd)
        while candidato and candidato not in visitados:
            if candidato in nos:
                return candidato
            visitados.add(candidato)
            candidato = pai_direto(candidato)
        return None

    raizes = []
    for hwnd in ordem:
        try:
            pai = resolver_pai(hwnd)
        except Exception:
            pai = None
        if pai is None:
            raizes.append(hwnd)
        else:
            nos[pai]["filhos"].append(hwnd)

    # 4) Impressão da árvore
    def imprimir(hwnd, prefixo="", ultimo=True, raiz=False):
        titulo = nos[hwnd]["titulo"]
        if raiz:
            print(titulo)
            prox_prefixo = "    "
        else:
            print(f"{prefixo}{'└── ' if ultimo else '├── '}{titulo}")
            prox_prefixo = prefixo + ("    " if ultimo else "│   ")
        filhos = nos[hwnd]["filhos"]
        for i, filho in enumerate(filhos):
            imprimir(filho, prox_prefixo, i == len(filhos) - 1)

    for i, hwnd in enumerate(raizes):
        imprimir(hwnd, raiz=True)
        if i < len(raizes) - 1:
            print()  # linha em branco entre árvores independentes

def diagnosticar_grade_uia():
    from pywinauto import Desktop

    titulo_janela = "Licenças / Afastamentos / Exames"
    titulo_grade = "Grade Licenças / Afastamentos"

    print("\n" + "=" * 80)
    print("DIAGNÓSTICO DA INTERFACE DE ACESSIBILIDADE DA GRADE")
    print("=" * 80)

    try:
        desktop = Desktop(backend="uia")

        janela = desktop.window(
            title_re=".*Licenças / Afastamentos / Exames.*"
        )
        janela.wait("exists", timeout=5)

        tabsheet = None

        for controle in janela.descendants():
            try:
                info = controle.element_info

                if (
                    info.class_name == "TTabSheet"
                    and info.name.strip() == titulo_grade
                ):
                    tabsheet = controle
                    break

            except Exception:
                continue

        if tabsheet is None:
            print(f"TTabSheet não encontrado: {titulo_grade}")
            return

        print(f"\nTTabSheet: {tabsheet.element_info.name}")
        print(f"Handle: {tabsheet.handle}")

        componentes = [tabsheet] + tabsheet.descendants()

        for controle in componentes:
            info = controle.element_info

            print("\n" + "-" * 80)
            print(f"Classe: {info.class_name}")
            print(f"Nome: {info.name!r}")
            print(f"Tipo UIA: {info.control_type}")
            print(f"Handle: {controle.handle}")

            try:
                elemento = info.element

                print(f"Tipo do objeto acessível: {type(elemento)}")

                for propriedade in (
                    "CurrentName",
                    "CurrentControlType",
                    "CurrentIsControlElement",
                    "CurrentIsContentElement",
                ):
                    try:
                        valor = getattr(elemento, propriedade)
                        print(f"{propriedade}: {valor}")
                    except Exception as erro:
                        print(f"{propriedade}: indisponível ({erro})")

                try:
                    padroes = elemento.GetSupportedPatterns()
                    print(f"Padrões de acessibilidade: {padroes}")
                except Exception as erro:
                    print(f"Padrões indisponíveis: {erro}")

            except Exception as erro:
                print(f"Não foi possível consultar o elemento: {erro}")

        print("\nDiagnóstico concluído.")

    except Exception as erro:
        print(f"Erro durante o diagnóstico: {erro}")

def diagnosticar_mensagens_grade():
    import win32gui
    import win32con

    titulo_janela = "Licenças / Afastamentos / Exames"
    titulo_grade = "Grade Licenças / Afastamentos"

    print("\n" + "=" * 80)
    print("DIAGNÓSTICO WIN32 DA GRADE")
    print("=" * 80)

    janelas = []

    def enumerar_janela(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return

        titulo = win32gui.GetWindowText(hwnd)

        if titulo_janela.casefold() in titulo.casefold():
            janelas.append(hwnd)

    win32gui.EnumWindows(enumerar_janela, None)

    if not janelas:
        print("Janela de Licenças não encontrada.")
        return

    hwnd_janela = janelas[0]

    print(f"Janela principal: {hwnd_janela}")

    tabsheets = []

    def enumerar_filhos(hwnd, _):
        classe = win32gui.GetClassName(hwnd)
        texto = win32gui.GetWindowText(hwnd)

        if (
            classe == "TTabSheet"
            and texto.strip() == titulo_grade
        ):
            tabsheets.append(hwnd)

    win32gui.EnumChildWindows(
        hwnd_janela,
        enumerar_filhos,
        None
    )

    if not tabsheets:
        print("TTabSheet da grade não encontrado.")
        return

    hwnd_tabsheet = tabsheets[0]
    grades = []

    def enumerar_grade(hwnd, _):
        classe = win32gui.GetClassName(hwnd)

        if classe in ("TcxGrid", "TcxGridSite"):
            grades.append(hwnd)

    win32gui.EnumChildWindows(
        hwnd_tabsheet,
        enumerar_grade,
        None
    )

    if not grades:
        print("TcxGrid/TcxGridSite não encontrados.")
        print("O componente pode não expor os filhos via Win32.")
        return

    for hwnd in grades:
        print("\n" + "-" * 60)
        print(f"Handle: {hwnd}")
        print(f"Classe: {win32gui.GetClassName(hwnd)}")
        print(f"Texto: {win32gui.GetWindowText(hwnd)!r}")
        print(f"Retângulo: {win32gui.GetWindowRect(hwnd)}")
        print(f"Pai: {win32gui.GetParent(hwnd)}")

        # WM_GETTEXT consulta texto convencional do controle.
        # Não envia cliques, teclas nem altera registros.
        try:
            tamanho = win32gui.SendMessage(
                hwnd,
                win32con.WM_GETTEXTLENGTH,
                0,
                0
            )

            print(f"WM_GETTEXTLENGTH: {tamanho}")

            buffer = win32gui.PyMakeBuffer(
                max(int(tamanho) + 2, 2)
            )

            resultado = win32gui.SendMessage(
                hwnd,
                win32con.WM_GETTEXT,
                len(buffer),
                buffer
            )

            print(f"WM_GETTEXT retorno: {resultado}")

        except Exception as erro:
            print(f"Consulta WM_GETTEXT indisponível: {erro}")

    print("\nDiagnóstico concluído.")

import ctypes
from ctypes import wintypes

import comtypes
import comtypes.client
from comtypes.automation import VARIANT


def diagnosticar_msaa_grade():
    """
    Inspeciona os filhos MSAA da TcxGrid e da TcxGridSite.
    Não clica nem altera os dados da grade.
    """

    import win32gui

    oleacc = ctypes.OleDLL("oleacc")

    # IID da interface IAccessible.
    iid_ia = comtypes.GUID(
        "{618736E0-3C3D-11CF-810C-00AA00389B71}"
    )

    oleacc.AccessibleObjectFromWindow.argtypes = [
        wintypes.HWND,
        wintypes.DWORD,
        ctypes.POINTER(comtypes.GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    oleacc.AccessibleObjectFromWindow.restype = ctypes.c_long

    oleacc.AccessibleChildren.argtypes = [
        ctypes.c_void_p,
        ctypes.c_long,
        ctypes.c_long,
        ctypes.POINTER(VARIANT),
        ctypes.POINTER(ctypes.c_long),
    ]
    oleacc.AccessibleChildren.restype = ctypes.c_long

    def consultar_propriedade(objeto, propriedade, child_id=0):
        """
        Consulta uma propriedade MSAA.
        Retorna o texto do erro caso a propriedade não esteja disponível.
        """
        try:
            metodo = getattr(objeto, propriedade)

            # Interfaces geradas pelo comtypes podem expor
            # propriedades indexadas como named_property.
            try:
                resultado = metodo[child_id]
            except (TypeError, AttributeError, KeyError):
                try:
                    resultado = metodo(child_id)
                except Exception:
                    nome_getter = f"get_{propriedade}"
                    getter = getattr(objeto, nome_getter, None)

                    if getter is None:
                        return "<indisponível>"

                    resultado = getter(child_id)

            if resultado is None:
                return ""

            return str(resultado)

        except Exception as erro:
            return f"<erro: {erro}>"

    def inspecionar_janela(hwnd, classe):
        print("\n" + "-" * 80)
        print(f"Classe: {classe} | Handle: {hwnd}")

        ponteiro = ctypes.c_void_p()

        hr = oleacc.AccessibleObjectFromWindow(
            hwnd,
            0,
            ctypes.byref(iid_ia),
            ctypes.byref(ponteiro),
        )

        print(f"AccessibleObjectFromWindow: 0x{hr & 0xFFFFFFFF:08X}")

        if hr != 0 or not ponteiro.value:
            print("Não foi possível obter a interface IAccessible.")
            return

        try:
            objeto = ctypes.cast(
                ponteiro,
                ctypes.POINTER(comtypes.IUnknown),
            )

            # Converte o ponteiro COM para uma interface IAccessible.
            objeto = ctypes.cast(
                ponteiro,
                ctypes.POINTER(comtypes.IUnknown),
            )

            interface = objeto.QueryInterface(iid_ia)

            try:
                quantidade = int(interface.accChildCount)
            except Exception as erro:
                print(f"Não foi possível ler accChildCount: {erro}")
                return

            print(f"Quantidade de filhos: {quantidade}")

            if quantidade <= 0:
                return

            filhos = (VARIANT * quantidade)()
            obtidos = ctypes.c_long(0)

            hr_filhos = oleacc.AccessibleChildren(
                ponteiro,
                0,
                quantidade,
                filhos,
                ctypes.byref(obtidos),
            )

            print(
                "AccessibleChildren: "
                f"0x{hr_filhos & 0xFFFFFFFF:08X}"
            )
            print(f"Filhos retornados: {obtidos.value}")

            for indice in range(obtidos.value):
                filho = filhos[indice]

                print(f"\nFilho [{indice + 1}]")
                print(f"  VARIANT.vt: {filho.vt}")

                # VT_I4 = 3: identificador de filho simples.
                if filho.vt == 3:
                    child_id = int(filho.value)
                    print(f"  Tipo: identificador MSAA ({child_id})")

                    for prop in (
                        "accName",
                        "accValue",
                        "accDescription",
                        "accRole",
                        "accState",
                    ):
                        print(
                            f"  {prop}: "
                            f"{consultar_propriedade(interface, prop, child_id)}"
                        )

                # VT_DISPATCH = 9 ou VT_UNKNOWN = 13:
                # o filho é outro objeto COM.
                elif filho.vt in (9, 13):
                    try:
                        filho_objeto = filho.value
                        print(f"  Tipo: objeto COM ({type(filho_objeto).__name__})")

                        # Se o VARIANT já expôs o objeto IDispatch,
                        # tentamos consultar as propriedades diretamente.
                        for prop in (
                            "accName",
                            "accValue",
                            "accDescription",
                            "accRole",
                            "accState",
                            "accChildCount",
                        ):
                            print(
                                f"  {prop}: "
                                f"{consultar_propriedade(filho_objeto, prop)}"
                            )

                    except Exception as erro:
                        print(f"  Erro ao examinar objeto COM: {erro}")

                else:
                    print(f"  Tipo VARIANT não tratado: {filho.vt}")

        finally:
            # Libera a referência COM obtida por AccessibleObjectFromWindow.
            ctypes.cast(
                ponteiro,
                ctypes.POINTER(comtypes.IUnknown),
            ).Release()

    print("\n" + "=" * 80)
    print("DIAGNÓSTICO MSAA — FILHOS DA GRADE")
    print("=" * 80)

    titulos = [
        "Licenças / Afastamentos / Exames",
    ]

    janela = None

    for titulo in titulos:
        hwnd = win32gui.FindWindow(None, titulo)
        if hwnd:
            janela = hwnd
            break

    if not janela:
        print("Janela principal não encontrada.")
        return

    grades = []

    def localizar_grades(hwnd, _):
        classe = win32gui.GetClassName(hwnd)

        if classe in ("TcxGrid", "TcxGridSite"):
            grades.append((hwnd, classe))

    win32gui.EnumChildWindows(janela, localizar_grades, None)

    if not grades:
        print("Nenhuma TcxGrid ou TcxGridSite encontrada.")
        return

    for hwnd, classe in grades:
        inspecionar_janela(hwnd, classe)

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

    parser.add_argument(
        "--lerNome",
        action="store_true",
        help="Procura informações de nome na janela principal."
    )

    parser.add_argument(
        "--lerPropriedadesNome",
        action="store_true",
        help="Investiga propriedades dos controles relacionados ao funcionário."
    )

    parser.add_argument(
        "--lerNomePreview",
        action="store_true",
        help="Lista os textos encontrados no preview da ficha financeira."
    )

    parser.add_argument(
        "--investigarFuncionario",
        action="store_true",
        help="Investiga os controles de seleção do funcionário."
    )

    parser.add_argument(
        "--lerListaFuncionario",
        action="store_true",
        help="Lê os itens do ListBox de funcionários."
    )

    parser.add_argument(
        "--listarJanelas",
        action="store_true",
        help="Lista o nome e o handle das janelas abertas."
    )

    parser.add_argument(
        "--diagnosticarGradeUIA",
        action="store_true",
        help="Investiga a grade de Licenças usando UI Automation."
    )

    parser.add_argument(
        "--diagnosticarMensagensGrade",
        action="store_true",
        help="Investiga mensagens Win32 do TcxGrid."
    )

    parser.add_argument(
        "--diagnosticarMSAAGrade",
        action="store_true",
        help="Investiga a acessibilidade MSAA da grade."
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

    if args.lerControlesImprimir:
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

    if args.lerNome:
        lerNome()

    if args.lerPropriedadesNome:
        lerPropriedadesNome()

    if args.lerNomePreview:
        ler_textos_preview()

    if args.investigarFuncionario:
        investigar_funcionario()

    if args.lerListaFuncionario:
        ler_lista_funcionario()

    if args.listarJanelas:
        listarJanelas()

    if args.diagnosticarGradeUIA:
        diagnosticar_grade_uia()

    if args.diagnosticarMensagensGrade:
        diagnosticar_mensagens_grade()      

    if args.diagnosticarMSAAGrade:
        diagnosticar_msaa_grade()

if __name__ == "__main__":
    main()