# Allmis ⛸️

En webbsida som visar när det är allmänhetens åkning (allmis) i Stora mossen.

Den är gjord för barn runt tio år: ett stort kort som säger om det är allmis idag och en lista över kommande sju dagar.

Sidan är helt statisk och publiceras med GitHub Pages från mappen `docs/`.

## Så fungerar det

1. En GitHub Action körs varje natt (03:00 UTC, alltså ca 05:00 på sommaren och 04:00 på vintern).
2. Skriptet `allmis/fetch.py` läser [dokumentsidan på ikgota.se](https://www.ikgota.se/ikgota/dokument#folder=73449),
   letar upp mappen **Istidsschema** och laddar ner alla `.xlsx`-filer där (en per vecka, ibland flera veckor per fil).
3. `allmis/parser.py` hittar alla pass som heter "Allmis" eller "Open ice" i flikarna med tidsrutnät
   (HCL Arena och A-Hallen) och räknar ut datum och tider.
4. Resultatet skrivs till `docs/allmis.json`, som `docs/index.html` läser.
5. Actionen committar filen. Eftersom tidsstämpeln `updated` ändras varje gång blir det en commit per körning,
   vilket också hindrar GitHub från att stänga av det schemalagda flödet efter 60 dagar utan aktivitet.

Om något går fel (sidan svarar inte, mappen saknas, en fil går inte att läsa) avbryts Actionen med ett tydligt
felmeddelande och `docs/allmis.json` lämnas orörd, så sidan visar fortfarande förra schemat.
Sidan visar "(kan vara gammalt)" om datan är äldre än två dygn.

### Hur Excel-filen läses

- Flikar där cell A1 är hallens namn och rad 1 har heltimmar (6, 7, 8 …) från kolumn C räknas som tidsrutnät.
  Varje kolumn är 30 minuter.
- Kolumn A är veckodagen (M T O T F L S) och kolumn B är dagen i månaden.
- Ett pass är en cell med text följd av tomma celler med samma bakgrundsfärg. Står det en tid i texten
  (t.ex. "Allmis 08.00–14.30, delad is") används den, annars räknas tiden ut från cellerna.
- Övrig text (t.ex. "delad is", "med klubba") visas som en liten notis.
- Veckonumret tas från filnamnet ("Vecka 44.xlsx"). Året väljs så att veckan hamnar närmast dagens datum.
- Pass samma dag i samma hall som ligger direkt efter varandra slås ihop.

## Köra lokalt

Kräver Python 3.9 eller senare och `make`.

```bash
make dev
```

Det skapar en virtuell miljö i `.venv`, hämtar det aktuella schemat till `docs/allmis.json`
och startar en webbserver på <http://localhost:1010>. Avsluta med Ctrl+C.

Andra kommandon:

| Kommando | Vad det gör |
|---|---|
| `make test` | Kör enhetstesterna mot sparade Excel-filer i `tests/fixtures/` |
| `make fetch` | Hämtar schemat och skriver `docs/allmis.json` |
| `make serve` | Startar bara webbservern (annan port: `make serve PORT=8080`) |
| `make clean` | Tar bort `.venv` |

## Köra Actionen manuellt

1. Gå till fliken **Actions** i repot på GitHub.
2. Välj **Uppdatera allmis** i listan till vänster.
3. Klicka **Run workflow** och sedan den gröna knappen **Run workflow**.

Eller med GitHub CLI:

```bash
gh workflow run update.yml
```

## Slå på GitHub Pages

1. Gå till **Settings → Pages** i repot.
2. Under **Build and deployment**, välj **Source: Deploy from a branch**.
3. Välj grenen `main` och mappen `/docs`, klicka **Save**.
4. Efter någon minut finns sidan på `https://<användarnamn>.github.io/<repo>/`.

Actionen behöver ingen extra inställning för att kunna committa `docs/allmis.json`: workflow-filen
ber själv om skrivrätt med `permissions: contents: write`. Får körningen ändå 403 vid `git push`,
välj **Read and write permissions** under **Settings → Actions → General → Workflow permissions**.

Actionen committar varje natt, så kör `git pull --rebase` innan du ändrar något lokalt.

## Uppdatera testfilerna

Om IK Göta ändrar formatet på Excel-filen: lägg den nya filen i `tests/fixtures/` med samma namn som på
hemsidan, skriv ett test i `tests/test_parser.py` och kör `make test`.
