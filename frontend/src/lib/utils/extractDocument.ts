import * as pdfjsLib from "pdfjs-dist";
import mammoth from "mammoth";
import * as XLSX from "xlsx";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.mjs",
  import.meta.url,
).href;

const PDF_MIMES = new Set([
  "application/pdf",
]);

const DOCX_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

const XLSX_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
]);

const PPTX_MIMES = new Set([
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "application/vnd.ms-powerpoint",
]);

const RTF_MIMES = new Set([
  "application/rtf",
  "text/rtf",
]);

const ODF_TEXT_MIMES = new Set([
  "application/vnd.oasis.opendocument.text",
]);

const ODF_SPREADSHEET_MIMES = new Set([
  "application/vnd.oasis.opendocument.spreadsheet",
]);

export function isSupportedDocument(mimeType: string): boolean {
  return (
    PDF_MIMES.has(mimeType) ||
    DOCX_MIMES.has(mimeType) ||
    XLSX_MIMES.has(mimeType) ||
    PPTX_MIMES.has(mimeType) ||
    RTF_MIMES.has(mimeType) ||
    ODF_TEXT_MIMES.has(mimeType) ||
    ODF_SPREADSHEET_MIMES.has(mimeType)
  );
}

async function extractPdf(file: File): Promise<string> {
  const data = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data }).promise;
  const pages: string[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const text = content.items.map((item: any) => item.str).join(" ");
    pages.push(text);
  }
  return pages.join("\n\n");
}

async function extractDocx(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  return result.value;
}

async function extractXlsx(file: File): Promise<string> {
  const data = await file.arrayBuffer();
  const workbook = XLSX.read(data, { type: "array" });
  const sheets: string[] = [];
  for (const name of workbook.SheetNames) {
    const sheet = workbook.Sheets[name];
    const csv = XLSX.utils.sheet_to_csv(sheet);
    sheets.push(`### Sheet: ${name}\n${csv}`);
  }
  return sheets.join("\n\n");
}

async function extractPptx(file: File): Promise<string> {
  const data = await file.arrayBuffer();
  const zip = await import("@zip.js/zip.js").then((m) => m.ZipReader);
  try {
    const reader = new zip(new Blob([data]));
    const entries = await reader.getEntries();
    const slides: string[] = [];
    const slideFiles = entries
      .filter((e) => e.filename?.match(/^ppt\/slides\/slide\d+\.xml$/))
      .sort((a, b) => a.filename.localeCompare(b.filename, undefined, { numeric: true }));

    for (const entry of slideFiles) {
      const writer = new Blob();
      const writable = new WritableStream({
        write(chunk) {
          return writer.write(chunk);
        },
      });
      await entry.getData!(writable);
      const text = await writer.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(text, "application/xml");
      const texts = Array.from(doc.querySelectorAll("a:t")).map((t) => t.textContent ?? "");
      if (texts.length > 0) {
        slides.push(texts.join(" "));
      }
    }
    return slides.join("\n\n");
  } catch {
    return "[Could not extract text from PPTX file]";
  }
}

function extractRtf(_file: File, rawText: string): string {
  const cleaned = rawText
    .replace(/\{\\[^{}]*\}/g, "")
    .replace(/\\[a-z]+\d*\s?/gi, "")
    .replace(/[{}]/g, "")
    .replace(/\\\n/g, "\n")
    .trim();
  return cleaned || "[Could not extract readable text from RTF file]";
}

function extractOdfText(_file: File, rawText: string): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(rawText, "application/xml");
  const texts = Array.from(doc.querySelectorAll("text\\:p, p")).map((p) => p.textContent ?? "");
  return texts.join("\n") || "[Could not extract text from ODF file]";
}

export async function extractDocumentText(file: File): Promise<string | null> {
  const mime = file.type;

  if (PDF_MIMES.has(mime)) {
    return extractPdf(file);
  }
  if (DOCX_MIMES.has(mime)) {
    return extractDocx(file);
  }
  if (XLSX_MIMES.has(mime)) {
    return extractXlsx(file);
  }
  if (PPTX_MIMES.has(mime)) {
    return extractPptx(file);
  }
  if (RTF_MIMES.has(mime)) {
    const rawText = await file.text();
    return extractRtf(file, rawText);
  }
  if (ODF_TEXT_MIMES.has(mime) || ODF_SPREADSHEET_MIMES.has(mime)) {
    const rawText = await file.text();
    return extractOdfText(file, rawText);
  }

  return null;
}
