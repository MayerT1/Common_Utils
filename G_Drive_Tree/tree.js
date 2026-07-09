/**
 * Generates a text tree of a Google Drive folder.
 *
 * Instructions:
 * 1. Replace FOLDER_ID with the ID of the folder to scan.
 * 2. Run makeDriveTree().
 * 3. A Google Doc named "Drive Folder Tree" will be created.
 */

const FOLDER_ID = "YOUR_FOLDER_ID_HERE";

function makeDriveTree() {
  const root = DriveApp.getFolderById(FOLDER_ID);

  let tree = root.getName() + "\n";
  tree += buildTree(root, "");

  const doc = DocumentApp.create("Drive Folder Tree");
  doc.getBody().setText(tree);

  Logger.log("Created: " + doc.getUrl());
}

function buildTree(folder, prefix) {
  let output = "";

  const folders = folder.getFolders();
  while (folders.hasNext()) {
    const sub = folders.next();
    output += `${prefix}├── ${sub.getName()}\n`;
    output += buildTree(sub, prefix + "│   ");
  }

  const files = folder.getFiles();
  while (files.hasNext()) {
    output += `${prefix}📄 ${files.next().getName()}\n`;
  }

  return output;
}