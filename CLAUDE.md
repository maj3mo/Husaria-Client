# StarLoco-Client — klient „Dofus Retro" (Electron)

Klient gry Dofus Retro (Electron + Flash player loader). Uruchamiany przez
`Dofus Retro.exe` w katalogu głównym tego podprojektu. Łączy się z lokalnym serwerem.

## Typ / build

- **Electron** (`package.json`, productName „Dofus Retro").
- Entry: `resources/app/preloader.js`. Kod klienta bytecode'owany (`bytenode`).
- Zależności: `flash-player-loader`, `electron-find-in-page`, `discord-rpc`, `i18n`, `regedit`.
- Gotowy plik: `Dofus Retro.exe` (~126 MB) w katalogu podprojektu — testerzy odpalają go wprost.

## Konfiguracja połączenia (kluczowe)

Plik `resources/app/retroclient/config.xml`:

- **Serwer logowania:** `127.0.0.1:450` (wpis „Dofus").
- **Dataserver (langi):** `http://127.0.0.1/` (priorytet 3) + lokalny fallback `data/`.
- Retry: `rdelay=3000ms`, `rcount=10`.

To ten plik decyduje, gdzie klient szuka Login (port 450) i skąd pobiera langi
(usługa `starloco_web` na porcie 80). Jeśli zmieniasz host/port serwera — zmieniasz tutaj.

## Reguły dla zmian

- Do gry potrzebny działający stack (`docker compose up -d`) — Login na 450 i Web na 80
  (langi). Bez langów klient nie załaduje tłumaczeń.
- Konto testowe: `test` / `test`, świat **Eratz** (601), wersja **1.39.8e**.
- Zmiana serwera docelowego = edycja `config.xml` (ip/port login + dataserver URL).
- Dystrybucja klienta / launcher dla testerów to EPIC 4 (MDE-35/MDE-36) — poza zakresem
  codziennych zmian serwera.

## Modowanie interfejsu gry (Flash/AS2)

- Cały UI gry (HUD, okna, przyciski) jest zaszyty w `resources/app/retroclient/loader.swf`
  (CWS, **Flash 8 → ActionScript 2**). Serwer NIE dostarcza aplikacji gry — mod = edycja
  lokalnego `loader.swf`. Brak plików XML interfejsu.
- **Framework UI = Ankama GAPI** (`gapi.ui.*`): okno = klasa `gapi.ui.<Nazwa>` + symbol
  `UI_<Nazwa>`; pasek HUD = `gapi.ui.Banner` z ikonami `UI_Banner<X>Icon`; klik ikony →
  metoda `displayUiOnClick`.
- Narzędzie: **JPEXS/ffdec**. GUI (JPEXS) po stronie usera do round-tripu i testu klienta.
  **CLI (ffdec)** działa też na hoście przez Javę z JetBrains **JBR** — wrapper
  `tools/ffdec.sh` (`-export`/`-replace`/`-importScript`/`-swf2xml`). Zawsze najpierw
  **round-trip PoC** (dekompiluj→zapisz bez zmian→sprawdź, czy klient wstaje). ✅ zaliczony w MDE-60.
- Cały UI (`gapi.ui.*`) jest **zobfuskowany** przez Ankamę → nie edytuje się źródła klas AS2;
  haki przez jawne API (`Banner.click({target:this._btnFriends})`) i wstrzykiwane skrypty.
- Rekonesans stringów bez Javy: rozpakuj CWS zlib-em w Pythonie i wyciągnij stałe AS2.
- **Dokumentacja modowania klienta** (czytaj przed każdym modem UI):
  - **`docs/modding-guide.md`** — szybki przepis krok-po-kroku (toolchain, ograniczenia, wzorce).
  - **`docs/client-reference.md`** — pełna ściąga: architektura klienta, `config.xml`, fakty
    `loader.swf`, cookbook ffdec CLI, mapy symboli/charId, wnętrze obfuskacji, gotowe szablony
    kodu, gotchas AS2, troubleshooting, dystrybucja.
  - `docs/MDE-60-hud-my-team.md` — worked example (przycisk HUD „My Team" + okno).
