# Mission reports in a shared Google Drive folder

Every mission can produce a report (`report.html` with the statistics and
both maps, `true_world.png`, `robot_map.png`, `metrics.json`). Reports are
saved locally under `reports/Mission #<n> - <date time> - <environment> (<machine>)/`
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
   of `Code.gs` with:

```javascript
const ROOT_FOLDER_ID = '1NJFC1WdeRxKdd7GiRqP2NmEqSGIGlvxe';   // the team folder

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const root = DriveApp.getFolderById(ROOT_FOLDER_ID);
    const folder = root.createFolder(data.name);
    data.files.forEach(f => folder.createFile(
      Utilities.newBlob(Utilities.base64Decode(f.b64), f.mime, f.name)));
    return json({ ok: true, url: folder.getUrl() });
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

- **Send report** (toolbar, or File menu) builds the report for the current
  mission and uploads it.
- With *auto-send* on (default) a report is sent automatically when a mission
  ends (returned, battery empty, fell).
- The status bar shows *report uploaded* / *offline – n report(s) waiting*;
  waiting reports are sent when the network returns or at the next start.
- **File → Open reports folder** shows the local copies.

Anyone who has the URL can add files to the folder, so share it only inside
the team. To change the script later, use **Deploy → Manage deployments →
Edit → New version**: the URL stays the same.
