# Document Upload and Analysis — User Guide

**Phase:** 9  
**Feature:** Form Upload and Document Analysis

---

## Overview

The AI Form Assistant now supports uploading your own PDF form. The system will:

1. Validate and securely store your document.
2. Structurally analyze it (page layout, text content, interactive fields).
3. Identify whether it matches a supported template.
4. Guide you through completing the form in your language.

---

## How to use it

### Step 1 — Select your language

From the landing page, click the **Upload Form** tab.

Use the **language buttons** to choose the language you want to use while answering questions:

| Button | Language |
|---|---|
| English | English |
| Deutsch | German |
| Français | French |
| العربية | Arabic (RTL layout) |

### Step 2 — Upload your PDF

Drag and drop a PDF onto the upload area, or click the area to open a file browser.

**Requirements:**

| Constraint | Limit |
|---|---|
| File type | PDF only |
| Maximum size | 10 MB |
| Maximum pages | 20 pages |

After selecting a file you will see:

- The **filename** and file size.
- A **Remove** button to choose a different file.
- An **Output language selector** to pick the language the completed form will be written in.

### Step 3 — Accept the privacy notice

Before uploading, you must accept the privacy notice:

> *Your uploaded document remains private and temporary. It will be deleted automatically after 24 hours.*

Tick the checkbox to enable the upload button.

### Step 4 — Upload and analyze

Click **Upload and Analyze**. You will see:

- An upload progress bar.
- An "Analyzing PDF structure…" spinner once the file is received.

### Step 5 — Review the analysis result

When analysis is complete, the system shows:

| Field | Meaning |
|---|---|
| Pages | Total number of pages |
| Type | Document classification |
| Contains Native Text | Whether digital text was found |
| Contains Interactive Form Fields | Whether fillable fields (AcroForm) exist |
| Contains Embedded Images | Whether images are embedded |

#### Analysis outcomes

| Next Step | Meaning | Action |
|---|---|---|
| **Supported Template Recognized** | The form matches a pre-defined template | Click **Start Guided Form** to begin |
| **OCR Recognition Needed** | The form is scanned/image-based | Not yet supported (Phase 10) |
| **Dynamic Field Detection Needed** | Digital but no template match | Not yet supported (Phase 11) |
| **Manual Review Required** | Analysis was inconclusive | Contact support |

### Step 6 — Start the guided form (supported templates only)

If the form matches a supported template, click **Start Guided Form**. You will be taken to the guided question-and-answer workflow, pre-loaded with the form fields from your uploaded document.

---

## Supported templates (Phase 9)

| Template | Description |
|---|---|
| Basic Registration v1 | Standard personal information form (first name, last name, date of birth, email, country, marital status) |

---

## Security and privacy

- Your document is validated for safety before processing. Files containing embedded JavaScript, auto-open actions, or attachments are rejected.
- Encrypted or password-protected PDFs are not accepted.
- Files are stored at a private, random path — never publicly accessible.
- Documents are automatically deleted after **24 hours**, regardless of session status.
- No document content is logged.
- Original filenames are sanitized before storage.

---

## Troubleshooting

### "Only PDF files are supported"

Make sure you are uploading a file with a `.pdf` extension.

### "File exceeds maximum size of 10MB"

Compress your PDF or use a different file. Most standard government forms are under 2 MB.

### "PDF is encrypted or password-protected"

Remove the password from your PDF before uploading. Use the owner/print password if available.

### "PDF contains active content (JavaScript, Launch Actions)"

The PDF was rejected for security reasons. Ask the form issuer for a version without active content.

### "Malformed PDF or corrupted structure"

The PDF could not be parsed. Try re-downloading the original form.

### "PDF exceeds the maximum page limit of 20 pages"

Phase 9 supports forms up to 20 pages. Contact support if you need to process a longer document.

---

## Manual form selection

If you prefer to select a form from the predefined list without uploading, switch to the **Select Manually** tab on the landing page and follow the original guided flow.
