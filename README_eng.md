# ZGeo-PG

**Language:** English | [Русский](README.md)

QGIS plugin for viewing spatial data stored in a PostgreSQL / PostGIS database.

Plugin version: **0.17.0**  
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
- the "Export" button offers "Export to Excel" or "Export to HTML"; both formats include a totals row that sums every numeric column (estimated rows, exact feature count, table size, spatial index size);
- on the **"Statistics"** tab, charts are displayed by table size and geometry type, as well as a statistics table by schema;
- statistics can also be exported to Excel or HTML, also with a totals row;
- the "Create all spatial indexes" button in the "Tables" toolbar (right after "Export") builds GiST indexes for all tables that have none, and "Refresh all spatial indexes" to its right rebuilds every existing one;
- the schema table on the "Statistics" tab has a "Spatial index" column (Yes/No); the right-click menu of a schema row showing "No" creates indexes for all of its tables;
- the right-click menu of a table row offers "Create spatial index" for "No" and "Refresh spatial index" plus "Drop spatial index" (with confirmation) for "Yes".

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
4. build and install with `scripts\build_zip.ps1` — only the latest archive stays in `dist`, and that version is installed into the QGIS 4.x profile;
5. commit.

## Installation in QGIS

### From ZIP archive

Build the archive:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_zip.ps1
```

The ready file will appear in `dist\zgeo-pg-0.17.0.zip`. Only the latest build is kept in `dist`. The script also installs the build into the QGIS Desktop 4.x profile (`%APPDATA%\QGIS\QGIS4\profiles\<profile>\python\plugins\zgeo-pg`); pass `-SkipQGISInstall` to only build the archive.

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
8. Click **"Export"** to export the list of tables to Excel.
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