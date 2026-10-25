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
        txt = txt.split('Mission #?').join('Mission #' + n).split('"mission_number": "?"').join('"mission_number": ' + n);
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
