# MDE-60 — Przycisk HUD „My Team" + okno dialogowe (mod loader.swf)

Notatka techniczna do modyfikacji interfejsu klienta. Fundament pod przyszłą pełną funkcję
**Team**; MVP: przycisk na banerze HUD otwierający okno „My Team" (placeholder).

## Ustalenia (rekonesans loader.swf)

Rozpoznane ze stringów `loader.swf` (bez pełnej dekompilacji — CWS rozpakowany zlib-em,
ekstrakcja stałych AS2). Fakty:

- `resources/app/retroclient/loader.swf` — CWS, **Flash 8 → ActionScript 2**, ~2,9 MB
  skompresowane / **6 128 428 B** rozpakowane. Zawiera całą aplikację gry + UI.
- **Framework UI = Ankama GAPI** (`gapi.ui.*`). Każde okno = klasa `gapi.ui.<Nazwa>` +
  symbol biblioteczny MovieClip `UI_<Nazwa>`. W SWF jest **135 okien** GAPI.
- **Pasek HUD = `gapi.ui.Banner`** (`UI_Banner`). Ikony na banerze to symbole
  `UI_Banner<X>Icon`: `Friends`, `Guild`, `Inventory`, `Map`, `Mount`, `Pvp`, `Spell`,
  `Stats`, `Book`, `Temporis`. Przyciski: `_btnFriends`, `_btnTabFriends`, `_btnBannerShortcuts`.
- **Hak otwierania okien = metoda `displayUiOnClick`** (znaleziona w stringach). To natywny
  mechanizm „klik ikony banera → pokaż UI". Nasz przycisk podłączamy tak samo.
- Serwer NIE dostarcza aplikacji gry (tylko dane `/lang/swf/*`) → mod = edycja **lokalnego**
  `loader.swf`; nie ma pliku XML interfejsu (układ zaszyty w AS2).

## Tablica symboli (dokładne charId — parser struktury SWF, sesja 2)

Wyciągnięte z `ExportAssets` przez `docs/swf_recon.py` (pure-Python, bez Javy — pełny
parser tagów SWF, nie tylko `grep` po stringach). **1318 nazwanych symboli**, **572 klasy
AS2** (`__Packages.*` = bloki `DoInitAction`), **1958** `DefineSprite`. To jest 1:1 to, co
zobaczysz w drzewie JPEXS — używaj tych nazw/ID przy klonowaniu.

| Rola | Symbol (MovieClip) | charId | Klasa AS2 (`__Packages.*`) |
|------|--------------------|--------|-----------------------------|
| Pasek HUD | `UI_Banner` | #1288 | `dofus..gapi.ui.Banner` (#20738) |
| Ikona-wzorzec (klonuj) | `UI_BannerFriendsIcon` | #1823 | — (symbol graficzny) |
| Okno-wzorzec A (drużyna) | `UI_Party` | #665 | `dofus..gapi.ui.Party` (#20891) |
| — element listy Party | `UI_PartyItem` / `UI_PartyItemInfo` | #662 / #664 | — |
| Okno-wzorzec B (znajomi) | `UI_Friends` | #975 | `dofus..gapi.ui.Friends` (#20957) |
| — element listy Friends | `UI_FriendsConnectedItem` / `...Disconnected...` | #1722 / #1720 | — |

**Pełny zestaw ikon banera** (do wyboru wzorca ikony): `UI_BannerFriendsIcon` #1823,
`GuildIcon` #1821, `InventoryIcon` #1819, `MapIcon` #1817, `MountIcon` #1816, `PvpIcon`
#1714, `SpellIcon` #1814, `StatsIcon` #1812, `BookIcon` #1838, `TemporisIcon` #1433.

**Ważne ustalenie:** w SWF **nie ma** żadnego okna „Team" — jedyne trafienia na „Team"
to `UI_GameResultTeam*` (ekrany wyników walki PvP, bez związku). Namespace **`MyTeam`
/ `UI_MyTeam` / `gapi.ui.MyTeam` jest wolny** — bez kolizji przy klonowaniu.

Odtworzenie: `python docs/swf_recon.py` (rozkład tagów + wszystkie symbole),
`python docs/swf_recon.py --grep Banner` (filtr nazw).

## Wzorce do sklonowania

| Element | Wzorzec | Uwagi |
|---------|---------|-------|
| Okno „My Team" | **`gapi.ui.Party`** lub **`gapi.ui.Friends`** | Party = drużyna (semantycznie najbliżej); Friends = lista graczy online/offline (`UI_FriendsConnectedItem`). Dla placeholdera oba OK — wybrać prostsze po podejrzeniu w JPEXS. |
| Ikona na banerze | **`UI_BannerFriendsIcon`** → klon `UI_BannerTeamIcon` | klon jednej z istniejących ikon `UI_Banner*Icon` |
| Podpięcie klik→okno | **`displayUiOnClick`** | tak działają istniejące przyciski banera |
| Ramka okna (skórka) | symbole `LightBrownWindow`, `ButtonClose`/`_btnClose` | natywny wygląd okna za darmo |

## Toolchain CLI (sesja 3 — ustawiony i sprawdzony)

Modujemy z linii poleceń, bez GUI: **ffdec CLI 26.2.1** (`tools/ffdec/`) pod Javą z
JetBrains **JBR** (host nie ma osobnej Javy; wrapper `tools/ffdec.sh` sam znajduje `java.exe`).
Sprawdzone: `tools/ffdec.sh -dumpAS2 loader.swf` czyta plik i listuje ścieżki skryptów AS2.

Kluczowe komendy: `-export`, `-replace <in> <out> <scriptpath> <patch.as>`,
`-importScript <in> <out> <folder>` (dodaje/nadpisuje), `-swf2xml`/`-xml2swf` (dowolne tagi).

Wstrzyknięcie Kroku 1 (do wyboru mechanizm — do potwierdzenia jednym testem):
`-importScript` z dołożonym `frame_1/DoAction` na sprite `UI_Banner`, albo edycja przez
`swf2xml→xml2swf`. Po wygenerowaniu zmodyfikowanego `loader.swf` — podmiana + test klientem (user).

## Narzędzie (GUI)

**JPEXS Free Flash Decompiler (FFDec)** (open-source, GUI, wymaga **Javy 8+**). Host projektu
**nie ma Javy**, więc dekompilacja/rekompilacja i testy klienta = praca desktopowa po stronie
usera. Obsługuje AS2 (edycja ActionScript **lub P-code/hex** + „Save"/„Import"). To standard
całej sceny modowania Dofusa — patrz [Referencje](#referencje).

> **Ryzyko rekompilacji AS2 (dlatego Krok 0 jest bramą):** dekompilator JPEXS jest
> dojrzalszy dla AS3 (AVM2) niż dla AS2 (AVM1) — rekompilacja wysokopoziomowego źródła AS2
> bywa kapryśna. Stąd: (a) round-trip PoC **przed** jakąkolwiek edycją, (b) fallback na
> **P-code/hex**, gdy edycja źródła się sypie, (c) preferuj **klonowanie istniejącego
> symbolu** (mniej nowego bytecode'u do rekompilacji) zamiast pisania okna od zera.

## Plan — malejące ryzyko (rób w tej kolejności)

### Krok 0 — round-trip PoC (brama; NAJPIERW) ✅ ZALICZONE (2026-07-17)
> Round-trip w JPEXS (`Save As` bez zmian → podmiana → klient wstał, wejście do gry OK).
> Potwierdza: (a) rekompilacja AS2 działa, (b) launcher NIE waliduje hasha `loader.swf`.
> Backup oryginału: `resources/app/retroclient/loader.swf.orig`.

1. **Backup** `loader.swf` (kopia poza klientem).
2. Otwórz `loader.swf` w JPEXS → **nic nie zmieniaj** → Save/Export do SWF.
3. Podmień plik w kliencie, uruchom `Dofus Retro.exe`, zaloguj `test`/`test`, wejdź na Eratz.
4. **Cel:** gra wstaje bez błędów. Potwierdza, że (a) rekompilacja AS2 tego SWF działa,
   (b) launcher (`main.jsc`) NIE waliduje hasha `loader.swf`.
   - Jeśli round-trip psuje klienta → nie edytuj AS wysokopoziomowo; pracuj na P-code /
     pojedynczych tagach, albo rozważ `modules/core.fla` w Adobe Animate.
   - Jeśli launcher waliduje hash → obejście przez `preloader.js` (czytelny, ładuje się
     przed `main.jsc`).

### Krok 1 — przycisk otwiera ISTNIEJĄCE okno (dowód mechaniki)
1. W JPEXS znajdź klasę `gapi.ui.Banner` i jak buduje przyciski (`_btnFriends`,
   `displayUiOnClick`).
2. Dodaj nowy przycisk na banerze (klon `UI_BannerFriendsIcon`), `onRelease` →
   `displayUiOnClick("Friends")` (na razie otwiera okno znajomych).
3. **Cel:** nowy przycisk widoczny na HUD, klik otwiera istniejące okno. Dowodzi, że nasz
   przycisk + hak działają — bez ryzyka własnego okna.

### Krok 2 — własne okno „My Team"
1. Sklonuj symbol `UI_Party` (lub `UI_Friends`) → `UI_MyTeam`; klasę `gapi.ui.Party` →
   `gapi.ui.MyTeam` (wytnij logikę specyficzną, zostaw ramkę + tytuł + `_btnClose`).
2. Ustaw tytuł „My Team" + placeholder (np. pole tekstowe „Wkrótce").
3. Przełącz `onRelease` przycisku z kroku 1 na `displayUiOnClick("MyTeam")`.
4. **Cel:** przycisk otwiera nasze okno „My Team", zamyka się natywnie.

### Krok 3 — repack / dystrybucja
Zmodyfikowany `loader.swf` do klienta testerów (styk z MDE-36).

## Stan realizacji (2026-07-17) — zrealizowane, In Review
- ✅ Krok 0 round-trip (JPEXS) — potwierdzony w grze.
- ✅ Krok 1 — przycisk na banerze otwiera okno (potwierdzony w grze; hak `click({target})`).
- ✅ Krok 2 — własny przycisk (klon `UI_BannerGuildIcon` obok `_btnMount`) + własne okno
  „My Team" (rysowane, styl natywny „Amis": brązowy pasek, beżowe tło, panel, czerwony X,
  przeciąganie za pasek tytułu, rozmiar 90%×90% ekranu, toggle).
- Realizacja przez **ffdec CLI** (`-importScript`), przejęty `on(construct)` `_btnTemporis`
  (Temporis nieużywany). Plik: `resources/app/retroclient/loader.mde60-krok2.swf`.
- Do Done (user): finalna podmiana `loader.swf` + potwierdzenie ostatniego builda; repack/
  dystrybucja = styk z MDE-36.

## Weryfikacja (warunek Done — po stronie usera)
Klient wstaje → przycisk widoczny na banerze HUD → klik otwiera okno „My Team" → X zamyka.

## Poza zakresem (przyszłość — pełna funkcja Team)
Roster / zaproszenia / synchronizacja = feature end-to-end: przycisk (ten) + nowy pakiet
protokołu 1.39.8 + handler w `StarLoco-Game` (Java + Lua). Tu tylko fundament kliencki.

## Obfuskacja klasy `Banner` + hak (sesja 3)

Dekompilacja klasy `Banner` w JPEXS wyszła **zobfuskowana** (Ankama): `§§push/§§pop`,
`§§goto`, fałszywe warunki `getTimer()`, metody jako znaki sterujące (`["\x1d\x15"]`).
**Edycja `Banner` na poziomie źródła AS2 odpada.** Ale:

- **Nazwy przycisków jawne**: `_btnFriends, _btnGuild, _btnMap, _btnStatsJob, _btnSpells,
  _btnInventory, _btnQuests, _btnPvP, _btnMount, _btnTemporis, _btnFights, _btnHelp,
  _btnNextTurn, _btnGiveUp`.
- **Publiczna metoda `click`** (nie-zobfuskowana): w kodzie wielokrotnie
  `this.click({target:this._btnFriends})` — centralny handler „otwórz okno przypisane do
  przycisku". **To nasz hak.**

### Mapa sprite `UI_Banner` (#1288) — `swf_recon.py --sprite UI_Banner`
Wszystkie przyciski to instancje **jednego symbolu `Button` (#47)** na timeline banera
(np. `_btnFriends` depth 51, `_btnHelp` depth 107). Sprite **nie ma skryptu klatki**
(41× PlaceObject2 + ShowFrame + End) — okablowanie w zobfuskowanej klasie → nasz `onRelease`
dodajemy jako NOWY skrypt.

### Krok 1 (finalny) — runtime-attach, bez edycji zobfuskowanego kodu ani strukturalnych
Hak `click({target})` potwierdzony w eksporcie (`Banner.as` linie 3200–3425). Jeden wstrzyknięty
skrypt na klatce sprite `UI_Banner` (`attachMovie` po linkage `UI_BannerFriendsIcon` #1823):
```actionscript
this.attachMovie("UI_BannerFriendsIcon", "_mcMyTeam", 9999);
this._mcMyTeam._x = 300;   // do dopasowania w grze
this._mcMyTeam._y = 0;
this._mcMyTeam.onRelease = function() {
    this._parent.click({target: this._parent._btnFriends});  // otwiera okno znajomych = dowód
};
```
Nasz nowy `on(release)`/skrypt piszemy czystym AS2 — JPEXS kompiluje od zera (obfuskacja
istniejących nie przeszkadza). Realizacja: `ffdec -replace` (auto) albo ręcznie w JPEXS.

### Eksport klienta (analiza)
Pełny eksport JPEXS: `S:\tttttt` (107 MB, tymczasowy). Kluczowe klasy w repo:
`docs/loader-decomp/gapi-ui/{Banner,Party,Friends,BannerSpriteInfos}.as`. **Cały `gapi.ui`
zobfuskowany** (nazwy pakietów URL-encoded, metody = znaki sterujące) → nie edytujemy źródła
klas; pracujemy przez jawne haki (`click`, nazwy `_btnX`) i wstrzykiwane skrypty.

## Referencje

Rozpoznanie sceny modowania Dofusa (sesja 2). Wnioski istotne dla naszej dekompilacji:

- **[JPEXS Free Flash Decompiler](https://github.com/jindrapetrik/jpexs-decompiler)** — nasze
  narzędzie. Obsługuje AS1/AS2/AS3, edycja jako źródło **albo P-code/hex/assembler**, „Save as
  SWF". [Lista funkcji (Wiki)](https://github.com/jindrapetrik/jpexs-decompiler/wiki/Features).
- **[scalexm/DofusInvoker](https://github.com/scalexm/DofusInvoker)** — pełne źródło klienta
  Dofus zdekompilowane JPEXS-em. **Dowód, że JPEXS radzi sobie z SWF-ami Ankamy** — ale to
  tylko referencja poglądowa, **nie źródło do kopiowania** (patrz różnica niżej).
- **[Flash SWF Editing — Nexus Mods Wiki](https://wiki.nexusmods.com/index.php/Flash_SWF_Editing)**
  — ogólny workflow edycji SWF; potwierdza fallback na P-code przy problemach z rekompilacją.

### Różnica: DofusInvoker (AS3) vs nasz `loader.swf` (AS2)

| | `DofusInvoker.swf` (repo scalexm) | nasz `loader.swf` (Retro) |
|---|---|---|
| Gra | Dofus **2.x** (nowoczesny) | Dofus **Retro 1.39.8** |
| ActionScript | **AS3** (Flash 11, AVM2, `DoABC`) | **AS2** (Flash 8, AVM1, `DoInitAction`) |
| Pakiety | `com.ankamagames.*`, `flash`, `mx`, `haxe` | `dofus..gapi.ui.*` (Ankama GAPI) |
| Dostęp do kodu UI | szyfrowany, doładowywany runtime (`DefineBinaryData`) → trik Run/FlashPlayer | **jawny, wprost w `loader.swf`** — bez szyfrowania/loadera |

**Konsekwencje dla nas:**
1. **Kodu z DofusInvokera nie przeklejamy** — inny bytecode (AVM2≠AVM1) i inna architektura UI.
   Nasza robota stoi na własnym rekonesansie (`swf_recon.py` + tablica symboli wyżej).
2. **Nasz przypadek jest prostszy** — cały UI Retro jest jawny w `loader.swf`, więc **nie
   potrzebujemy** przechwytywania szyfrowanych SWF-ów (którego wymaga Dofus 2.x).
3. **Ale AS2 to wyższe ryzyko rekompilacji** niż AS3 → round-trip PoC (Krok 0) jest krytyczny,
   a klonowanie symboli bezpieczniejsze niż pisanie od zera (patrz box w sekcji „Narzędzie").

## Jak odtworzyć rekonesans (CLI, bez Javy)
Pełny parser struktury SWF (tagi + `ExportAssets`) jest w `docs/swf_recon.py`:
```bash
cd sources/StarLoco-Client/docs
python swf_recon.py                 # rozkład tagów + wszystkie 1318 symboli
python swf_recon.py --grep Banner   # filtr po nazwie symbolu
```
Szybki grep po stałych stringach (starszy sposób, tylko stringi, nie struktura):
```bash
cd sources/StarLoco-Client/resources/app/retroclient
python -c "import zlib,re; raw=zlib.decompress(open('loader.swf','rb').read()[8:]); \
print('\n'.join(sorted(set(s.decode('latin1') for s in re.findall(rb'[\x20-\x7e]{4,}', raw)))))" \
  | grep -Ei 'gapi.ui|Banner|displayUi'
```
