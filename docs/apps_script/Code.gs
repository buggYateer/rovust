const ROOT_FOLDER_ID = '1NJFC1WdeRxKdd7GiRqP2NmEqSGIGlvxe';   // the team folder

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const root = DriveApp.getFolderById(ROOT_FOLDER_ID);
    const lock = LockService.getScriptLock();
    lock.waitLock(30000);
    let n, folder = null;
    try {
      // a run that already sent a report keeps its number and its folder (key = one run of the app)
      const props = PropertiesService.getScriptProperties();
      const known = data.key ? props.getProperty('key_' + data.key) : null;
      if (known) {
        const k = known.split('|');
        n = parseInt(k[0], 10);
        if (k[1]) { try { folder = DriveApp.getFolderById(k[1]); } catch (e) { folder = null; } }
      } else {
        // next mission number = highest "Mission #n" already in the folder + 1
        n = 0;
        const it = root.getFolders();
        while (it.hasNext()) {
          const m = it.next().getName().match(/^Mission #(\d+)/);
          if (m) n = Math.max(n, parseInt(m[1], 10));
        }
        n += 1;
      }
      const suffix = data.suffix || data.name.replace(/^Mission #\S+ - /, '');
      if (!folder) folder = root.createFolder('Mission #' + n + ' - ' + suffix);
      if (data.key) props.setProperty('key_' + data.key, n + '|' + folder.getId());
    } finally {
      lock.releaseLock();
    }
    const name = folder.getName();
    // each report of the run is its own sub-folder: Report 1 - 20-15-30, Report 2 - ...
    const target = data.report ? folder.createFolder(data.report) : folder;
    data.files.forEach(f => {
      let bytes = Utilities.base64Decode(f.b64);
      if (f.mime.indexOf('text/') === 0 || f.mime === 'application/json') {
        // write the final number into the report itself
        let txt = Utilities.newBlob(bytes).getDataAsString('UTF-8');
        txt = txt.split('Mission #new').join('Mission #' + n).split('"mission_number": "new"').join('"mission_number": ' + n);
        bytes = Utilities.newBlob(txt, f.mime).getBytes();
      }
      target.createFile(Utilities.newBlob(bytes, f.mime, f.name));
    });
    return json({ ok: true, number: n, name: name, url: folder.getUrl() });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

function doGet() { return json({ ok: true, service: 'Rovust reports' }); }

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
