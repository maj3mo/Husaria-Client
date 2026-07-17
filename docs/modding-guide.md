# Poradnik: tworzenie i edycja elementów w kliencie (loader.swf / AS2)

Wielorazowy playbook (szybki start) do modowania interfejsu klienta Dofus Retro.
- Pełna ściąga (architektura, cookbook ffdec, mapy symboli, szablony, troubleshooting):
  [`client-reference.md`](client-reference.md).
- Worked example: [MDE-60](MDE-60-hud-my-team.md) — przycisk HUD + własne okno.

## 1. Fakty bazowe

- Cały UI gry (HUD, okna, przyciski) jest w `resources/app/retroclient/loader.swf`
  (**CWS, Flash 8 → ActionScript 2 / AVM1**, ~6 MB rozpakowane). Serwer dostarcza tylko dane
  (`/lang/swf/*`), nie aplikację → mod = edycja lokalnego `loader.swf`.
- Framework UI = **Ankama GAPI** (`gapi.ui.*`): okno = klasa `gapi.ui.<Nazwa>` + symbol
  `UI_<Nazwa>`; pasek HUD = sprite `UI_Banner` (#1288), przyciski = instancje `Button` (#47).
- Launcher **NIE waliduje hasha** `loader.swf` → można podmieniać plik swobodnie.
  **Zawsze rób backup**: `cp loader.swf loader.swf.orig` (revert: odwrotnie).

## 2. Toolchain (host, bez osobnej instalacji Javy)

- **ffdec CLI** (JPEXS) w `tools/ffdec/`, uruchamiany przez wrapper **`tools/ffdec.sh`**,
  który sam znajduje Javę z JetBrains **JBR** (`C:\Program Files\JetBrains\*/jbr/bin/java.exe`).
- **`docs/swf_recon.py`** — parser struktury bez Javy: rozkład tagów, `ExportAssets`
  (`--grep <nazwa>`), rozłożone instancje sprite (`--sprite UI_Banner`: depth/charId/instance).
- GUI **JPEXS** (Java) po stronie usera — do round-trip PoC i podglądu; test klientem też user.

Komendy ffdec: `-dumpAS2`, `-export script <dir> <swf>`, `-replace`, `-importScript <in> <out> <folder>`,
`-swf2xml`/`-xml2swf`.

## 3. Twarde ograniczenia (KLUCZOWE — czytaj przed modem)

1. **`gapi.ui` jest zobfuskowany** (Ankama): JPEXS/ffdec nie odtwarza czytelnego AS2
   (metody = znaki sterujące `["\x1d\x15"]`, `§§push/§§pop`, `§§goto`). → **Nie edytuj źródła
   istniejących klas.** Pracuj tylko przez: (a) jawne, nie-zobfuskowane haki, (b) **własne,
   nowe** skrypty AS2 (kompilują się czysto).
2. **ffdec CLI jest replace-only** — `-replace`/`-importScript` podmieniają istniejący skrypt,
   **nie dodają nowych tagów** (nowego frame `DoAction`, nowego `PlaceObject`). → Żeby
   „wstrzyknąć" kod, **przejmij istniejący clip-event** czystym AS2.
3. **AS2 gotcha — rodzic połyka kliknięcia dzieci**: jeśli kontener ma `onPress`/`onRelease`,
   jego dzieci-przyciski NIE dostają zdarzeń. → Drag i przyciski trzymaj w **osobnych dzieciach**,
   kontener bez handlerów.
4. Nowe okna doczepiaj do `_root` (`createEmptyMovieClip` / `attachMovie`); rozmiar z
   `Stage.width`/`Stage.height`. Jeśli renderuje się pod grą — przepnij na warstwę HUD.
5. Nie-zobfuskowany kod da się rekompilować; polskie znaki bywają problematyczne w SWF v8 —
   dla pewności używaj ASCII w tekstach.

## 4. Przepis: wstrzyknięcie kodu (replace-only workaround)

Najczęstszy wzorzec — przejąć clip-event istniejącej instancji, w której scope masz dostęp
do potrzebnego rodzica. Dla HUD dobry, bezpieczny cel: **`on(construct)` przycisku
`_btnTemporis`** (sezonowy Temporis nieużywany na naszym serwerze; baner i tak go ukrywa).

```bash
cd S:/huasaria-retro
D="tools/work/inject/DefineSprite_1288_UI_Banner/frame_1/PlaceObject2_47_Button_75"
mkdir -p "$D"
cp sources/StarLoco-Client/resources/app/retroclient/loader.swf tools/work/loader.swf
# ...zapisz swój kod do: "$D/CLIPACTIONRECORD on(construct).as"
./tools/ffdec.sh -importScript tools/work/loader.swf tools/work/loader_mod.swf tools/work/inject
```
Ścieżka folderu = układ z `-export script` (`DefineSprite_<id>_<nazwa>/frame_1/PlaceObject2_<char>_<sym>_<depth>/CLIPACTIONRECORD on(<event>).as`). ID/depth/instance sprawdź:
`python docs/swf_recon.py --sprite UI_Banner`.

## 5. Gotowe haki i wzorce

- **Otwarcie istniejącego okna banera** (natywnie): `banner.click({target: banner._btnFriends})`
  — `click` jest publiczne/nie-zobfuskowane; tak działają skróty klawiszowe. Cele:
  `_btnFriends, _btnGuild, _btnInventory, _btnMap, _btnSpells, _btnStatsJob, _btnQuests,
  _btnPvP, _btnMount, _btnFights`.
- **Nowa ikona na banerze**: `banner.attachMovie("UI_BannerGuildIcon","_mcX",depth)` — linkage
  z `ExportAssets` (ikony: `UI_Banner{Friends,Guild,Inventory,Map,Mount,Pvp,Spell,Stats,Book}Icon`).
- **Własne okno** (skórka natywna niedostępna — `Window` #97 to pusty sprite, chrome rysuje
  zobfuskowana klasa): rysuj samodzielnie na `_root` (paleta „Amis": pasek `0x4B3E2C`, tło
  `0xD8CFA6`, panel `0xC6BC8E`, X `0xC0392B`, tytuł biały). Drag = osobne dziecko „titleBar",
  X = osobne dziecko. Wzorzec w `on(construct)` z MDE-60 (patrz historia issue / ten build).

## 6. Weryfikacja i dostarczenie

- Kompilacja: `-importScript` bez błędów + obecność Twoich stringów w SWF
  (`python -c "import zlib; b=zlib.decompress(open('out.swf','rb').read()[8:]); print(b'MojString' in b)"`).
- Czysta kompilacja: `-export script <dir> out.swf` i odczyt swojego pliku = 1:1 źródło.
- **Test klientem robi user** (wejście do gry, wygląd, zachowanie) — typowy warunek Done.
- Dostarczaj jako osobny plik (`loader.mde<NN>-...swf`), nie nadpisuj `loader.swf` do czasu testu.

## 7. Skalowanie na przyszłość

- Do edycji strukturalnych (nowy tag/instancja/symbol), których CLI nie robi → JPEXS GUI
  jednorazowo, potem skrypty przez CLI. Ewentualne `swf2xml→xml2swf` dla dowolnych tagów.
- **Fork JPEXS + MCP = przekombinowane** — ffdec CLI wystarcza; wracać do tematu tylko przy
  dużym wolumenie modów lub potrzebie własnych pasów deobfuskacji.
