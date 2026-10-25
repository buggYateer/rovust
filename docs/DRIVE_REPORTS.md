# Mission reports in a shared Google Drive folder

Every mission can produce a report (`report.html` with the statistics and
both maps, `true_world.png`, `robot_map.png`, `metrics.json`). Reports are
saved locally under `reports/Mission #<n> - <title>/`, where the title is the
name typed when sending or, by default, `<date time> - <environment> (<machine>)`.
**The mission number is given by the Drive folder itself:** the bridge looks
at the folders already there and uses the next number, so numbers are unique
for the whole team (a report that has not been uploaded yet is called
`Mission #new - ...`)
and, once the bridge below is set up, uploaded into **one shared Drive
folder** for the whole team — from any teammate's computer, with no Google
login in the program. If the computer is offline, the report waits in
`reports/pending.json` and is sent automatically when the network is back.

The bridge is a tiny Google Apps Script that runs under *your* Google
account and writes into *your* folder. One person does this once.

## 1. Create the script (5 minutes)

1. Open the shared Drive folder in the browser. Its URL looks like
   `https://drive.google.com/drive/folders/1AbC...xyz` — copy the part after
   `folders/`: that is the **folder ID**.
2. Go to <https://script.google.com> → **New project**. Replace the contents
   of `Code.gs` with the code below (also in `docs/apps_script/Code.gs`):

```javascript
const ROOT_FOLDER_ID = '1NJFC1WdeRxKdd7GiRqP2NmEqSGIGlvxe';   // the team folder

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const root = DriveApp.getFolderById(ROOT_FOLDER_ID);
    // next mission number = highest "Mission #n" already in the folder + 1
    let n = 0;
    const it = root.getFolders();
    while (it.hasNext()) {
      const m = it.next().getName().match(/^Mission #(\d+)/);
      if (m) n = Math.max(n, parseInt(m[1], 10));
    }
    n += 1;
    const suffix = data.suffix || data.name.replace(/^Mission #\S+ - /, '');
    const name = 'Mission #' + n + ' - ' + suffix;
    const folder = root.createFolder(name);
    data.files.forEach(f => {
      let bytes = Utilities.base64Decode(f.b64);
      if (f.mime.indexOf('text/') === 0 || f.mime === 'application/json') {
        // write the final number into the report itself
        let txt = Utilities.newBlob(bytes).getDataAsString('UTF-8');
        txt = txt.split('Mission #new').join('Mission #' + n).split('"mission_number": "new"').join('"mission_number": ' + n);
        bytes = Utilities.newBlob(txt, f.mime).getBytes();
      }
      folder.createFile(Utilities.newBlob(bytes, f.mime, f.name));
    });
    return json({ ok: true, number: n, name: name, url: folder.getUrl() });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

function doGet() { return json({ ok: true, service: 'PyRov reports' }); }

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
```

3. The team folder ID is already in `ROOT_FOLDER_ID` (from the folder link
   `drive.google.com/drive/folders/1NJFC1WdeRxKdd7GiRqP2NmEqSGIGlvxe`). Save
   (Ctrl+S) and name the project *PyRov reports*.
4. **Deploy → New deployment** → type **Web app**:
   - *Execute as*: **Me**
   - *Who has access*: **Anyone**
   - Deploy, authorise with your Google account when asked (click
     *Advanced → Go to PyRov reports (unsafe)* on the warning: it is your own
     script).
5. Copy the **Web app URL** (ends in `/exec`).

## 2. Tell PyRov about it

Put the URL in `report_config.json` at the root of the project (commit it, so
everyone gets it):

```json
{
  "upload_url": "https://script.google.com/macros/s/AKfy.../exec",
  "auto_send": true
}
```

Or in the program: **File → Report settings…**, paste the URL, Save.

## 3. Use it

- **Send report** (toolbar, or File menu) asks for a name for the report
  (or sends it with the automatic name), builds it for the current mission
  and uploads it.
- With *auto-send* on (default) a report is sent automatically when a mission
  ends (returned, battery empty, fell).
- The status bar shows *report uploaded* / *offline – n report(s) waiting*;
  waiting reports are sent when the network returns or at the next start.
- **File → Open reports folder** shows the local copies.

Anyone who has the URL can add files to the folder, so share it only inside
the team.

## Updating the script

When `Code.gs` changes in this repository, paste the new code into the Apps
Script editor, save, then **Deploy → Manage deployments → ✎ (edit) → Version:
New version → Deploy**. The URL stays the same, so nothing changes in PyRov.
