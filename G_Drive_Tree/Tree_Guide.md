# Google Drive Tree

A small Google Apps Script that generates a text representation of a Google Drive folder hierarchy.

Example output:

```text
Project
├── Docs
│   ├── Requirements.docx
│   └── Notes.md
├── Images
│   └── Logo.png
└── README.md
```

## Setup

1. Go to https://script.google.com
2. Create a new project.
3. Paste the contents of `drive_tree.gs`.
4. Replace:

```javascript
const FOLDER_ID = "YOUR_FOLDER_ID_HERE";
```

with the ID of your Google Drive folder.

Example folder URL:

```
https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
```

Folder ID:

```
1AbCdEfGhIjKlMnOpQrStUvWxYz
```

## Run

Select **makeDriveTree** from the function dropdown and click **Run**.

The first execution will request authorization.

## Output

A Google Doc named **Drive Folder Tree** will be created in your Google Drive containing the folder hierarchy.