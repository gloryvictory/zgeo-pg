# ZGeo-PG

**Language:** English | [Русский](README.md)

QGIS plugin for viewing spatial data stored in a PostgreSQL / PostGIS database.

Plugin version: **0.30.0**  
Release history: [change.log](change.log)

The plugin adds a **"ZGeo-PG"** toolbar panel in QGIS with a **"ZGeo-PG Catalog"** button that opens a floating panel. In the panel:

- the top part displays the plugin version;
- the top-right corner has an **"EN" / "RU"** button to switch the interface between English and Russian without restarting QGIS; the selected language is saved;
- on the **"Connections"** tab, you configure the database connection: host, port, database name, user and password; "Save connection" writes the parameters both to the QGIS settings and to a local database `<QGIS profile>/zgeo-pg/connections.sqlite`, which is read on the next QGIS start (the form is filled with the last used connection);
- the same tab has the "Connect" / "Disconnect" button, and loading a saved connection connects right away;
- the status bar shows a green dot with "Connected" while a connection is open and a red dot with "Not connected" otherwise;
- the window title shows the current plugin version;
- after connecting, the **"Tables"** tab shows a list of all spatial tables with schema name, table name, table comment, geometry column, geometry type, SRID, estimated row count, exact row count, data size and the size of the other indexes; then the spatial index presence, its name and size, and finally "Full size" (data + other indexes + spatial index);
- row count and table size values are loaded in the background with the ability to interrupt; the loader uses its own connection, so the "Refresh" button reloads the list without reconnecting;
- above the list there is a filter by table name and schema selection; there is a "Only with geometry" filter;
- the "Information" button on the "Tables" tab opens a dialog with full details of the selected table, including its comment and spatial index;
- save your QGIS project before running the build: the script closes the editor and, if it has not exited within 10 seconds, terminates the process;
- the "Export" button offers "Export to Excel" or "Export to HTML"; both formats include a totals row that sums every numeric column (estimated rows, exact feature count, data size, indexes size, spatial index size, full size), and every size is written in human-readable form — KB, MB, GB, TB;
- on the **"Statistics"** tab, charts are displayed by table size and geometry type, as well as a statistics table by schema;
- statistics can also be exported to Excel or HTML, also with a totals row;
- the "Create all spatial indexes" button in the "Tables" toolbar (right after "Export") builds GiST indexes for all tables that have none, and "Refresh all spatial indexes" to its right rebuilds every existing one;
- the schema table on the "Statistics" tab has a "Spatial index" column (Yes/No); the right-click menu of a schema row showing "No" creates indexes for all of its tables;
- the right-click menu of a table row offers "Create spatial index" for "No" and "Refresh spatial index" plus "Drop spatial index" (with confirmation) for "Yes".

- the **"Geospatial data quality"** tab runs 10 checks: invalid geometry, empty geometry, duplicate geometries, self-intersections, mixed geometry types, wrong SRID, coordinates out of range, degenerate features, unclosed rings and a missing spatial index; every check is switched on with its checkbox and the "i" button opens the check description and the way to fix it on the right;
- the checks run in a background thread over every loaded table; the "Run checks", "Abort" and "Export" (Excel or HTML) buttons sit at the bottom of the tab, the name of the current check is shown above the status bar and its progress in the status bar, and the results fill a table × check grid with the problem cells highlighted;
- the **"Attribute data quality"** tab offers the same set of tools for 11 attribute checks: NULL values, empty strings, leading and trailing spaces, double spaces, duplicate records, numbers stored as text, control characters, abnormal text length, outliers in numeric columns dates out of the reasonable range and attribute duplicates; the last check unites exact duplicate rows, composite key duplicates, matches ignoring case and extra spaces, and partial matches with the match percentage (for example "ЯмалоНенецкий автономный окру" inside "ЯмалоНенецкий автономный округ" is 96.7 %), and a double click on the cell opens the detailed list with export; a check runs only on columns of a matching type and shows "Not applicable" when there are none;
- the **"Reference data quality"** tab splits the panel in two: on the left and on the right you pick a connection, a table and a text field, and the sorted lists of unique values are shown below; the "Compare" button sits between the panels with the statistics "Matched", "Present in the left panel but not in the right", "Present in the right panel but not in the left" underneath;
- the right-click menu of the statistics table (and a double click on a row) opens the list of the chosen category on the right, including the verdict row "Everything from the left panel is present in the right" (its value is only "Yes" or "No", and the list shows the values missing on the right); each panel list and the comparison result are exported to Excel or HTML: Excel gets a "Statistics" sheet plus one sheet per category ("Matched", "Present in the left panel but not in the right", "Present in the right panel but not in the left"), and HTML gets one page with a link panel on top, then "Selected sources" (connection, table and field of both sides), "Statistics" and the value tables of every category;
- picking an entry in the "Connection" list connects to it at once, and a green or red dot left of the list shows whether it worked (the error text is in the tooltip);
- when the table list is empty the tab explains why: "Connected, but the database has no tables" or "Connected, but no privilege to read tables: <name> (tables in the database: N)";
- both sides of the reference data tab see the connection the panel is using even when it was never saved, and refresh the list on connect, save and delete; an unreachable database reports an error and the tab keeps working;
- check titles, summaries, full descriptions and fix hints are translated into English and follow the interface language, including already rendered results and an open description.

The plugin supports QGIS 3.16 and newer, including QGIS 4 / Qt 6.

## Project Structure

```text
zgeo-pg/
├── __init__.py          # classFactory entry point
├── README.md            # documentation in Russian
├── README_eng.md        # documentation in English
├── metadata.txt         # QGIS plugin metadata
├── change.log           # release history (English)
├── plugin.py            # toolbar button and panel lifecycle
├── panel.py             # floating panel, list and statistics tab
├── i18n.py              # translations dictionary and language switching
├── connection.py        # PostgreSQL connections and the local SQLite parameter store
├── catalog.py           # read list of spatial tables from PostGIS
├── stats.py             # aggregate tables for statistics
├── charts.py            # bar charts without external dependencies
├── load_task.py         # background loading of table characteristics
├── quality.py           # spatial and attribute data quality checks
├── nsi.py               # reference data comparison: tables, fields, unique values
├── info_dialog.py       # "Table Information" dialog
├── explorer.py          # open files in Explorer
├── formatting.py        # formatting sizes and numbers
├── excel_export.py      # write tables to .xlsx without external dependencies
├── html_export.py       # write tables to .html without external dependencies
├── table_export.py      # export tables with file selection
├── version.py           # plugin version from metadata.txt
├── icon.svg             # plugin icon
├── LICENSE.md           # MIT license
├── scripts/             # build scripts
└── .gitignore           # ignored files
```

## Release

Workflow for every task:

1. bump the version in `metadata.txt` and prepend a line to its `changelog`;
2. fill `change.log` in English (new section on top);
3. update `README.md` and `README_eng.md`;
4. build and install with `scripts\build_zip.ps1` — only the latest archive stays in `dist`, and that version is installed into the QGIS 4.x profile (the script closes and reopens QGIS itself);
5. commit.

## Installation in QGIS

### From ZIP archive

Build the archive:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_zip.ps1
```

The ready file will appear in `dist\zgeo-pg-0.30.0.zip`. Only the latest build is kept in `dist`. The script first closes a running QGIS Desktop (it keeps the plugin files locked, so the copy fails otherwise), installs the build into the QGIS Desktop 4.x profile (`%APPDATA%\QGIS\QGIS4\profiles\<profile>\python\plugins\zgeo-pg`) and starts QGIS again. Pass `-SkipQGISInstall` to only build the archive, and `-NoRestart` to leave QGIS closed.

Or install it manually. In QGIS open:

**Plugins > Manage and Install Plugins > Install from ZIP**

and select the built archive.

### Manually

Copy the `zgeo-pg` folder entirely to the QGIS plugins directory:

- Windows QGIS 4: `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\`
- Windows QGIS 3: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
- Linux: `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/`
- macOS: `~/Library/Application Support/QGIS/QGIS4/profiles/default/python/plugins/`

Then enable **ZGeo-PG** in the QGIS plugin manager.

After updating the plugin, close QGIS completely and restart. If the **"ZGeo-PG"** panel does not appear, open **Plugins > Manage and Install Plugins**, find **ZGeo-PG** and make sure it is enabled.

## Usage

1. On the **"ZGeo-PG"** toolbar, click the **"ZGeo-PG Catalog"** button (or select **Plugins > ZGeo-PG > ZGeo-PG Catalog**).
2. If needed, switch the language with the **"EN" / "RU"** button in the top-right corner of the panel.
3. Open the **"Connections"** tab and configure the connection to the PostgreSQL database with PostGIS extension.
4. Click the **"Connect"** button.
5. After connecting, the **"Tables"** tab will show a list of all spatial tables. The coordinate system, row count and table size are loaded automatically in the background.
6. Use filters to search for tables by name or select a specific schema.
7. Select a table and click the **"Information"** button to view detailed information.
8. Click **"Export"** to export the list of tables to Excel or HTML; sizes in the file are written as KB/MB/GB.
9. Open the **"Statistics"** tab to view charts and statistics by schema.

The last selected connection is remembered and used as the starting point for the next launch.

## Supported Versions

- QGIS 3.16 and newer
- PostgreSQL 12+ with PostGIS 3.0+ extension

## Requirements

- QGIS must have the QPSQL driver (included with QGIS)
- The database must have the PostGIS extension installed
- The user must have rights to read tables and PostGIS system views

## License

MIT License — see LICENSE.md file