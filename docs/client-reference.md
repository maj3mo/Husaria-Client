# Reference: edycja klienta Dofus Retro (pełna ściąga)

Encyklopedia do modowania klienta. Szybki przepis krok-po-kroku → [`modding-guide.md`](modding-guide.md).
Worked example → [`MDE-60-hud-my-team.md`](MDE-60-hud-my-team.md).

Spis:
1. Architektura klienta  2. `config.xml`  3. `loader.swf` (fakty)  4. Toolchain
5. Cookbook ffdec CLI  6. `swf_recon.py`  7. Obfuskacja (wnętrze)  8. Mapa symboli / charId
9. Gotowe szablony kodu  10. Gotchas AS2  11. Weryfikacja i dostarczenie  12. Troubleshooting
13. Dystrybucja  14. Odtworzenie pełnego eksportu

---

## 1. Architektura klienta

- **Electron** (`Dofus Retro.exe`, ~126 MB, productName „Dofus Retro"). Testerzy odpalają exe wprost.
- Entry: `resources/app/preloader.js`; kod klienta **bytecode'owany bytenode** (`main.jsc`).
- Zależności: `flash-player-loader`, `electron-find-in-page`, `discord-rpc`, `i18n`, `regedit`.
- Katalog gry: `resources/app/retroclient/`
  - `loader.swf` — cała aplikacja gry + UI (patrz §3),
  - `preloader.swf` — mały loader (538 B),
  - `config.xml` — konfiguracja połączenia (§2),
  - `data/` — lokalny fallback langów.
- **Launcher nie waliduje hasha `loader.swf`** → podmiana pliku jest bezpieczna. Zawsze backup
  `loader.swf.orig`.

## 2. `config.xml` (połączenie)

`resources/app/retroclient/config.xml`:
- **Login**: `127.0.0.1:450` (wpis „Dofus").
- **Dataserver (langi)**: `http://127.0.0.1/` (priorytet 3) + fallback `data/`.
- Retry: `rdelay=3000ms`, `rcount=10`.
- Zmiana serwera docelowego = edycja ip/port login + dataserver URL tutaj.
- Konto testowe `test`/`test`, świat **Eratz** (601), wersja **1.39.8e**.

## 3. `loader.swf` — fakty

- **CWS, Flash 8 → ActionScript 2 (AVM1)**. Rozpakowany body: **6 128 428 B**
  (CWS = zlib od bajtu 8: `zlib.decompress(open(f,'rb').read()[8:])`).
- Zawartość (z `swf_recon.py`): **1318** nazwanych symboli (`ExportAssets`), **1958**
  `DefineSprite`, **569** `DoInitAction`, **572** klasy AS2 (`__Packages.*`), 1 główny `DoAction`.
- Framework = **Ankama GAPI** (`gapi.ui.*`): **135 okien**, każde = klasa `gapi.ui.<Nazwa>` +
  symbol `UI_<Nazwa>`. Klasa jest zarejestrowana do symbolu (`Object.registerClass`) → MovieClip
  `UI_<Nazwa>` JEST instancją klasy.

## 4. Toolchain

| Narzędzie | Gdzie | Do czego |
|-----------|-------|----------|
| **ffdec CLI** 26.2.1 | `tools/ffdec/` + wrapper `tools/ffdec.sh` | export/replace/import/xml — automat z Basha |
| **Java (JBR)** | `C:\Program Files\JetBrains\*/jbr/bin/java.exe` | runtime ffdec (host nie ma osobnej Javy) |
| **`swf_recon.py`** | `sources/StarLoco-Client/docs/` | rekonesans struktury bez Javy |
| **JPEXS GUI** | maszyna usera (Java) | round-trip PoC, podgląd, test klientem |

`tools/ffdec.sh` sam znajduje JBR java. Ponowne pobranie ffdec:
`https://github.com/jindrapetrik/jpexs-decompiler/releases`.

## 5. Cookbook ffdec CLI

```bash
# Lista skryptów AS2 (ścieżki do -replace/-import)
tools/ffdec.sh -dumpAS2 <swf>

# Lista tagów
tools/ffdec.sh -dumpSWF <swf>

# Eksport źródeł (script | image | shape | all | fla ...)
tools/ffdec.sh -export script <outdir> <swf>
tools/ffdec.sh -export all    <outdir> <swf>     # wszystko (wolne, ~100 MB)

# Podmiana JEDNEGO skryptu (replace-only!)
tools/ffdec.sh -replace <in> <out> "<scriptName>" <patch.as>

# Bulk import z drzewa folderów (układ jak -export script) — TEŻ replace-only
tools/ffdec.sh -importScript <in> <out> <folder>

# Dowolne edycje tagów (dodawanie/usuwanie) — reprezentacja bytecode
tools/ffdec.sh -swf2xml <swf> <xml>
tools/ffdec.sh -xml2swf <xml> <out.swf>
```

**Layout folderu dla `-importScript`** (mirror `-export script`):
```
<folder>/DefineSprite_<id>_<nazwa>/frame_<n>/DoAction.as
<folder>/DefineSprite_<id>_<nazwa>/frame_<n>/PlaceObject2_<char>_<sym>_<depth>/CLIPACTIONRECORD on(<event>).as
<folder>/__Packages/...  (klasy — zobfuskowane, nie ruszać)
```

**Ograniczenie krytyczne:** `-replace`/`-importScript` **podmieniają istniejący** skrypt,
**nie tworzą nowych tagów** (frame `DoAction`, `PlaceObject`). Dodanie nowego elementu → §7/§9.

## 6. `swf_recon.py`

```bash
cd sources/StarLoco-Client/docs
python swf_recon.py                    # rozkład tagów + wszystkie 1318 symboli
python swf_recon.py --grep Banner      # filtr nazw symboli (ExportAssets)
python swf_recon.py --sprite UI_Banner # placed instances sprite: depth / charId / instance name
```

## 7. Obfuskacja (wnętrze — jak z nią żyć)

- **Cały `gapi.*` jest zobfuskowany.** JPEXS/ffdec zwraca rozjechany kod: `§§push/§§pop`,
  `§§goto`, fałszywe warunki (`if(!ord("\x05"))`, `getTimer()+1`), a **nazwy metod/pól = ciągi
  znaków sterujących** (np. `["\x1d\x15"]`). Nazwy pakietów w ścieżkach eksportu są
  URL-encoded (`__Packages/dofus/%1D%19%10/gapi/ui/Banner.as`).
- **Nie rekompiluj zobfuskowanych klas** — nie da się ich odtworzyć. Rekompilować da się tylko
  **nowy, czysty** kod AS2 (kompiluje się bezbłędnie).
- **Zobfuskowane metody można WOŁAĆ** przez bracket-notation z dokładnym ciągiem znaków:
  ```actionscript
  this.api.ui["\x1a\x09\x09"]("Friends");   // (OBSERWOWANE) menedżer UI: pokaż okno po nazwie
  ```
  W `Banner.as` widać `this.api.ui["\x1a\t\t"]("MovableBar")` / `("FightOptionButtons")` —
  to publiczny loader UI po nazwie. **Status: obserwowane, nie zweryfikowane w grze** — używać
  eksperymentalnie; pewny hak to `Banner.click({target})` (§8/§9).
- Jawne (nie-zobfuskowane), potwierdzone: metoda **`Banner.click({target:...})`**, nazwy pól
  `_btn*`, `attachMovie` po linkage `UI_*`, standardowe API Flasha (`attachMovie`,
  `createEmptyMovieClip`, `startDrag`, `Stage.*`).

## 8. Mapa symboli / charId (pasek HUD)

Sprite **`UI_Banner` (#1288)** — przyciski = instancje symbolu **`Button` (#47)**:

| instance | depth | | instance | depth |
|----------|-------|-|----------|-------|
| `_btnInventory` | 46 | | `_btnQuests` | 53 |
| `_btnMap` | 47 | | `_btnPvP` | 54 |
| `_btnSpells` | 48 | | `_btnFights` | 55 |
| `_btnStatsJob` | 49 | | `_btnMount` | 74 |
| `_btnNextTurn` | 50 | | `_btnTemporis` | 75 |
| `_btnFriends` | 51 | | `_btnHelp` | 107 |
| `_btnGuild` | 52 | | `_btnGiveUp` | 138 |

Inne instancje na banerze: `_cChat` (Chat #1276), `_msShortcuts` (#1273), `_pvAP`/`_pvMP`
(ActionPointsViewer #1272), `_hHeart` (Heart #1270), `_txtConsole`, `_circleXtra`.

**Ikony banera** (linkage do `attachMovie`): `UI_BannerFriendsIcon` #1823, `GuildIcon` #1821,
`InventoryIcon` #1819, `MapIcon` #1817, `MountIcon` #1816, `PvpIcon` #1714, `SpellIcon` #1814,
`StatsIcon` #1812, `BookIcon` #1838, `TemporisIcon` #1433.

**Okna / skórki**: `Window` #97 (**pusty sprite** — chrome rysuje zobfuskowana klasa
`gapi.Window`, brak gotowej skórki do doczepienia), `UI_Party` #665 (`gapi.ui.Party`),
`UI_Friends` #975 (`gapi.ui.Friends`), `ButtonClose` #2085. Pełny wykaz: `swf_recon.py --grep`.

## 9. Gotowe szablony kodu (kopiuj-wklej)

### 9a. Wstrzyknięcie (przejęcie clip-eventu) — bezpieczny cel `_btnTemporis`
`tools/work/inject/DefineSprite_1288_UI_Banner/frame_1/PlaceObject2_47_Button_75/CLIPACTIONRECORD on(construct).as`

### 9b. Przycisk na banerze → istniejące okno (natywnie)
```actionscript
on(construct)
{
   var _p = this._parent;                       // baner (Banner instance)
   _p.attachMovie("UI_BannerGuildIcon","_mcMyTeam",9990);
   _p._mcMyTeam._x = _p._btnMount._x + 30;
   _p._mcMyTeam._y = _p._btnMount._y;
   _p._mcMyTeam.onRelease = function()
   {
      this._parent.click({target:this._parent._btnFriends});   // otwiera okno znajomych
   };
}
```

### 9c. Przycisk → własne okno (skórka „Amis", drag, X, 90% ekranu, toggle)
Pełny, sprawdzony wzorzec (MDE-60): kontener BEZ handlerów, drag na dziecku `titleBar`,
zamykanie na dziecku `closeBtn` (patrz §10 gotcha #1). Rozmiar z `Stage.width/height`.
```actionscript
_p._mcMyTeam.onRelease = function()
{
   var r = _root;
   if(r._myTeamWin) { r._myTeamWin.removeMovieClip(); return; }   // toggle
   var sw = Stage.width; var sh = Stage.height;
   if(!sw || sw < 100) { sw = 800; } if(!sh || sh < 100) { sh = 600; }
   var W = Math.round(sw * 0.9); var H = Math.round(sh * 0.9);
   var win = r.createEmptyMovieClip("_myTeamWin", r.getNextHighestDepth());
   win._x = Math.round(sw * 0.05); win._y = Math.round(sh * 0.05);
   // tło + ramka
   win.lineStyle(2,0x2E2519,100); win.beginFill(0xD8CFA6,100);
   win.moveTo(0,0); win.lineTo(W,0); win.lineTo(W,H); win.lineTo(0,H); win.lineTo(0,0); win.endFill();
   // panel listy
   win.lineStyle(1,0x8A7B5C,100); win.beginFill(0xC6BC8E,100);
   win.moveTo(10,44); win.lineTo(W-10,44); win.lineTo(W-10,H-12); win.lineTo(10,H-12); win.lineTo(10,44); win.endFill();
   // pasek tytułu + nagłówek panelu
   win.lineStyle(); win.beginFill(0x4B3E2C,100);
   win.moveTo(0,0); win.lineTo(W,0); win.lineTo(W,34); win.lineTo(0,34); win.lineTo(0,0); win.endFill();
   win.beginFill(0x6B5D45,100);
   win.moveTo(10,44); win.lineTo(W-10,44); win.lineTo(W-10,66); win.lineTo(10,66); win.lineTo(10,44); win.endFill();
   // teksty (selectable=false → nie łapią myszy)
   var f = new TextFormat(); f.font = "_sans"; f.size = 15; f.bold = true; f.color = 0xFFFFFF;
   win.createTextField("t",31,12,7,300,22); win.t.selectable = false; win.t.text = "My Team"; win.t.setTextFormat(f);
   // drag — osobne dziecko (przezroczysty hit)
   var bar = win.createEmptyMovieClip("titleBar",5);
   bar.beginFill(0x000000,0); bar.moveTo(0,0); bar.lineTo(W,0); bar.lineTo(W,34); bar.lineTo(0,34); bar.lineTo(0,0); bar.endFill();
   bar.onPress = function(){ this._parent.startDrag(); };
   bar.onRelease = function(){ this._parent.stopDrag(); };
   bar.onReleaseOutside = function(){ this._parent.stopDrag(); };
   // zamykanie — osobne dziecko (czerwony X)
   var c = win.createEmptyMovieClip("closeBtn",20);
   c.lineStyle(1,0x7A1E14,100); c.beginFill(0xC0392B,100);
   c.moveTo(W-28,7); c.lineTo(W-7,7); c.lineTo(W-7,28); c.lineTo(W-28,28); c.lineTo(W-28,7); c.endFill();
   var fx = new TextFormat(); fx.font = "_sans"; fx.size = 14; fx.bold = true; fx.color = 0xFFFFFF;
   c.createTextField("x",1,W-24,8,16,18); c.x.selectable = false; c.x.text = "X"; c.x.setTextFormat(fx);
   c.onRelease = function(){ this._parent.removeMovieClip(); };
};
```

## 10. Gotchas AS2 (katalog)

1. **Rodzic z handlerem połyka kliknięcia dzieci.** Kontener z `onPress`/`onRelease` przejmuje
   zdarzenia — dzieci-przyciski przestają działać. → drag i przyciski w OSOBNYCH dzieciach,
   kontener bez handlerów. (To był bug „X nie zamyka".)
2. **Nie-`selectable` textfield przepuszcza mysz**; `selectable=true` przechwytuje (blokuje drag).
   Ustawiaj `.selectable = false` na etykietach.
3. **Grafika (`lineTo`/`beginFill`) renderuje się POD dziećmi** (textfields, klipy). Kolejność
   wizualna = depth dzieci, nie kolejność rysowania.
4. **Fonty**: dynamiczny tekst na `_sans`/`_serif` (device font) renderuje bez osadzania.
   **Polskie znaki bywają psute w SWF v8 → używaj ASCII** w tekstach.
5. **`Stage.width/height`** = rozmiar sceny (Dofus: `scaleMode=noScale` → piksele ekranu).
6. **`attachMovie(linkage, name, depth[, init])`** wymaga nazwy z `ExportAssets` (linkage).
7. **`registerClass`**: MovieClip `UI_<Nazwa>` jest instancją klasy `gapi.ui.<Nazwa>` — stąd
   `this._parent` w clip-evencie dziecka banera = instancja `Banner`, ma metodę `click`.
8. **Toggle**: trzymaj referencję (`_root._myTeamWin`) i usuwaj `removeMovieClip()` przy ponownym kliku.

## 11. Weryfikacja i dostarczenie

```bash
# 1. kompilacja bez błędów: -importScript nic nie wypisuje na błąd; stringi obecne:
python -c "import zlib; b=zlib.decompress(open('out.swf','rb').read()[8:]); print(b'MojString' in b)"
# 2. czysta kompilacja: re-export i porównaj swój plik ze źródłem (1:1)
tools/ffdec.sh -export script <dir> out.swf   # (wolne dla całości; uważaj na timeout)
```
- **Test klientem robi user** (wejście do gry, wygląd, zachowanie) — typowy warunek Done.
- Dostarczaj jako OSOBNY plik `loader.mde<NN>-...swf`; `loader.swf` podmieniaj dopiero po teście.
- Backup: `loader.swf.orig`; revert `cp loader.swf.orig loader.swf`.

## 12. Troubleshooting

| Objaw | Przyczyna / fix |
|-------|-----------------|
| `-importScript` wypisuje błędy kompilacji | Twój AS2 się nie kompiluje — popraw składnię; zobfuskowanych klas NIE ruszaj |
| Stringi Twojego kodu nieobecne w SWF | patch nie wszedł (zła ścieżka folderu / próba dodania nowego tagu — replace-only) |
| Klient nie wstaje po podmianie | revert `loader.swf.orig`; sprawdź round-trip; nie edytowałeś zobfuskowanej klasy? |
| Okno nie widać (jest pod grą) | doczepione za nisko — zamiast `_root` użyj warstwy HUD (rodzic banera) |
| Krzyżyk/przycisk nie klika | gotcha §10 #1 (rodzic połyka) — rozdziel drag i przyciski na dzieci |
| Ikona w złym miejscu / niewidoczna | pozycjonuj względem widocznego przycisku; fallback gdy cel `._visible==false` |
| Polskie znaki krzaczą | użyj ASCII (SWF v8) |

## 13. Dystrybucja (MDE-36)

Zmodyfikowany `loader.swf` trafia do paczki testerów w ramach **EPIC 4 / MDE-36** (launcher /
instrukcja). Do czasu dystrybucji mody trzymamy jako osobne pliki `loader.mde<NN>-*.swf`.

## 14. Odtworzenie pełnego eksportu (do głębokiej analizy)

```bash
tools/ffdec.sh -export all <outdir> sources/StarLoco-Client/resources/app/retroclient/loader.swf
```
~107 MB / ~10 tys. plików. Kluczowe klasy referencyjne (zobfuskowane) trzymamy w repo:
`docs/loader-decomp/gapi-ui/{Banner,Party,Friends,BannerSpriteInfos}.as`.
```
