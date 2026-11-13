# AuxiliarInterface

Biblioteca Python para **localizar, investigar, diagnosticar e automatizar** interfaces gráficas
Windows — de aplicativos Delphi/DevExpress antigos a aplicativos modernos — sem reescrever sempre
a mesma enumeração de janelas, foco, mouse e acessibilidade.

## Instalação

```bash
pip install -e .          # ou: pip install pywinauto comtypes
```

Requer Windows e Python ≥ 3.9. Dependências: `pywinauto` (backends `win32`/`uia`, teclado) e
`comtypes` (MSAA). `pywin32` é instalado como dependência do `pywinauto`; a biblioteca usa
`ctypes` para a API Win32. A importação funciona em qualquer SO (útil para testes); recursos
Win32 só rodam no Windows.

## Estrutura

```
main.py                         # CLI
auxiliar_interface/
  api.py                        # DesktopAutomation (ponto de entrada)
  config.py                     # Settings, NoiseFilter (toda configuração fica aqui)
  exceptions.py
  core/      models, locator (Criteria), backend, context, element, window, control
  native/    win32 (ctypes), uia (pywinauto), msaa (comtypes/oleacc)
  automation/ mouse, keyboard, focus, actions (valores por mensagens Win32)
  inspection/ hierarchy, properties, accessibility, hints, grid, diagnostics
  utils/     formatting (Report), logging, waiting
  cli.py
tests/                          # unittest, sem aplicativos externos
```

## Localizar janelas

```python
from auxiliar_interface import DesktopAutomation

aux = DesktopAutomation(backend="win32")           # ou "uia"

j = aux.window(title="Form1")                      # título exato (ignora o & de atalho)
j = aux.window(title_contains="Folha")             # parcial
j = aux.window(title_re=".*Gerador de Relatórios.*")   # regex (re.match, como o pywinauto)
j = aux.window(class_name="TfrPrintForm", visible=True) # combinando critérios
j = aux.window(handle=1575844)                     # por handle (não dependa de handles fixos!)

j.exists(); j.wait_for_exists(timeout=10); j.wait_for_gone(); j.is_active()
j.owned_windows(); j.owner(); j.tree()             # relações e hierarquia
aux.windows(visible=True)                          # todas as janelas
aux.active_window(); aux.window_tree()             # janela ativa e árvore pai/proprietária
```

`aux.window(...)` é **preguiçoso**: guarda os critérios e resolve o handle quando necessário;
se a janela for fechada e reaberta com outro handle, a próxima operação a encontra de novo.
Critérios: `title, title_contains, title_re, class_name (str ou lista), class_name_re, handle,
visible, enabled, has_text, process_id, automation_id, control_type, inside, at_point, predicate,
ignore_case, index`. Combine com `Criteria(...) & Criteria(...)`.
Com `Settings(strict=True)`, critério ambíguo levanta `AmbiguousMatchError`.

## Localizar controles

```python
j.controls()                         # todos os descendentes
j.children()                         # só filhos diretos
j.controls(class_name="TEdit", has_text=False)    # sem texto
j.controls(visible=False)            # invisíveis
j.controls(enabled=False)            # desabilitados
j.controls(inside=Rect(0, 0, 300, 100))           # por posição
c = j.control(class_name="TBitBtn", title="&OK")  # preguiçoso
c.rect, c.handle, c.parent(), c.ancestors(), c.has_focus()
aux.control_at()                     # controle sob o mouse (ou control_at(x, y))
aux.focused_control()                # controle com foco
```

## Clicar, digitar e preencher

```python
c.click()                            # centro do controle; valida existência/visibilidade/habilitação
c.click(offset=(315, 20))            # relativo ao canto do controle (erro se fora dele)
c.double_click(); c.right_click()
c.click(method="message")            # BM_CLICK/WM_*BUTTON, sem mover o mouse
c.click(method="invoke")             # padrão Invoke do UIA (backend uia)

campo.set_text("João")               # foca, limpa e digita (dispara eventos do app)
campo.set_text("João", method="message")   # WM_SETTEXT
campo.type_text("abc", clear=True)
combo.select("Item 2"); combo.items(); lista.value()
chk.check(); chk.uncheck(); chk.is_checked()

aux.keyboard.press("tab", 2); aux.keyboard.hotkey("ctrl", "shift", "s")
aux.mouse.click(x, y); aux.mouse.drag((10, 10), (200, 80))
```

Antes de interagir a biblioteca confere se o controle existe, está visível e habilitado, e se o
ponto do clique realmente pertence a ele (`verify=False` desativa). `Settings(focus_policy=...)`:
`auto` (ativa a janela só se necessário), `never`, `force`.

## Investigar foco

```python
aux.focus.current()                              # controle com foco
aux.focus.wait_for_change(timeout=5)             # aguardar mudança
aux.focus.wait_for(Criteria(class_name="TEdit"))
aux.focus.trace_tab(10)                          # INTERAÇÃO: TAB N vezes registrando o foco
```

## Win32, UIA e MSAA

| Tecnologia | Onde | Observações |
|---|---|---|
| Win32 (ctypes) | `native/win32.py`, `DesktopAutomation(backend="win32")` | Rápido; ideal para Delphi/VCL. Assinaturas declaradas uma vez, tipos corretos em 32/64 bits. |
| UIA (pywinauto) | `backend="uia"`, `inspection/accessibility.py` | Elementos sem HWND, padrões (Invoke, Value, Grid...). |
| MSAA (comtypes) | `native/msaa.py` | `IAccessible`: nome, valor, estado, filhos. Só leitura. |

A biblioteca **não promete** que um backend exponha o que o aplicativo não publica: o relatório
mostra o que cada fonte devolveu, inclusive "nada". Leitura de texto (`Settings.text_source`):
`fast` (GetWindowText), `message` (WM_GETTEXT) ou `auto` (padrão: WM_GETTEXT quando o controle
filho vem vazio — necessário em Edits Delphi/DevExpress).

## Diagnósticos (somente leitura)

```python
aux.diagnosticar_janela("Form1")                   # ou aux.diagnostics.window(Criteria(...))
aux.diagnosticar_controle(handle=123456)
aux.diagnosticar_foco()
aux.diagnosticar_mouse()
aux.diagnosticar_hierarquia("Form1")
aux.diagnostics.grid(Criteria(title_re=".*Licenças.*"), tab_title="Grade Licenças / Afastamentos")
```
Todos devolvem um `Report` (`.render()`, `.to_dict()`, `.to_json()`). Hints
(`Control.hint()`, `inspection.hints.probe_hints`) **movem o mouse**, o que é inerente a provocar
Hints; o cursor é restaurado ao final.

## CLI

```bash
python main.py windows list [--visible|--hidden] [--untitled] [--no-noise-filter]
python main.py windows inspect --title-contains Folha
python main.py windows tree

python main.py controls list --title "Form1" --backend win32 [--class TEdit] [--no-text] [--direct]
python main.py controls inspect --handle 123456
python main.py controls inspect --title "Form1" --class TelLookupCombo
python main.py controls properties --title "Form1" [--sources native,pywinauto,uia,msaa] [--all]
python main.py controls tree --title "Form1" --depth 5

python main.py focus inspect
python main.py mouse inspect [--delay 3] [--accessibility]
python main.py mouse monitor

python main.py diagnostics window --title "Form1" [--accessibility]
python main.py diagnostics uia   --title-re ".*Licenças.*"
python main.py diagnostics msaa  --title-re ".*Licenças.*" --class TcxGrid --depth 2
python main.py diagnostics grid  --title-re ".*Licenças.*" --tab-title "Grade Licenças / Afastamentos"
```

Comandos que **interagem** (marcados `[INTERAÇÃO]` na ajuda): `controls click`, `controls hover`,
`focus trace`, `mouse click`, `mouse move`, `hints probe`. Todos os outros são somente leitura.
Opções gerais: `--backend`, `--timeout`, `--focus`, `--text-source`, `--json`, `-v/-vv`.
Códigos de saída: 0 ok, 1 não encontrado, 2 uso/erro, 3 plataforma.

### Migração das funções antigas

| Antiga | Nova |
|---|---|
| `lerScreen`, `listarJanelas` | `windows list`, `windows tree` |
| `lerBotoes` | `windows inspect` |
| `lerBotoes2`, `lerControles`, `lerControlesImprimir`, `lerNome`, `ler_textos_preview` | `controls list` (`--has-text`, `--window-class`...), `controls tree` |
| `diagnosticoWin32` | `diagnostics window` |
| `testarFoco`, `testarTeclado` | `focus trace` + `focus inspect` |
| `lerHints` | `hints probe` |
| `lerPropriedades`, `lerPropriedadesNome` | `controls properties` |
| `investigar_funcionario`, `ler_lista_funcionario` | `controls inspect --class TelLookupCombo` / `--handle` (itens de listas em `items`) |
| `lerControleMouse`, `monitorarMouse`, `testarCliqueMouse` | `mouse inspect`, `mouse monitor` |
| `clicarOndeEstaOMouse` | `mouse click --delay 3` |
| `clicarImprimir`, `testarPosicaoImprimir` | `controls click --offset X,Y`, `controls hover --offset X,Y` |
| `diagnosticar_grade_uia`, `_mensagens_grade`, `_msaa_grade` | `diagnostics grid` (ou `uia` / `msaa`) |

## Testes

```bash
python -m unittest discover -s tests -t .      # também funciona com pytest
```
Os testes usam um backend falso em memória (localização, filtros, hierarquia, timeouts, erros,
formatação, CLI). **Não** exercitam Win32/UIA/MSAA reais: valide-os no Windows com seu aplicativo.
