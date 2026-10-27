// Writes the weekly report .docx from report.json (built by src/report.py).
// usage: node report/docx_report.js build/report.json docs/reports/hisobot-YYYY-MM-DD.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, HeadingLevel, AlignmentType,
  WidthType, ShadingType, BorderStyle, LevelFormat, PageBreak, Footer, PageNumber, TableLayoutType,
} = require("docx");

const [, , jsonPath, outPath] = process.argv;
const doc = JSON.parse(fs.readFileSync(jsonPath, "utf8"));

const INK = "2B2117", MUTED = "6B5A45", ACCENT = "8C3B22", RULE = "B9A27C", HEAD_FILL = "EFE6D2";
const PAGE_W = 11906, MARGIN = 1134, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, 2 cm margins

function scaleWidths(widths) {
  const sum = widths.reduce((a, b) => a + b, 0);
  const out = widths.map((w) => Math.floor((w * CONTENT_W) / sum));
  out[out.length - 1] += CONTENT_W - out.reduce((a, b) => a + b, 0);
  return out;
}

function cell(text, width, { header = false, align = AlignmentType.LEFT, size = 18 } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: header ? { type: ShadingType.CLEAR, color: "auto", fill: HEAD_FILL } : undefined,
    margins: { top: 40, bottom: 40, left: 70, right: 70 },
    children: [new Paragraph({ alignment: align, children: [new TextRun({ text: String(text), bold: header, size, color: header ? INK : undefined })] })],
  });
}

function table(b) {
  const widths = scaleWidths(b.widths);
  const small = b.header.length > 6 ? 16 : 18;
  const border = { style: BorderStyle.SINGLE, size: 4, color: RULE };
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    layout: TableLayoutType.FIXED,
    borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
    rows: [
      new TableRow({ tableHeader: true, children: b.header.map((h, i) => cell(h, widths[i], { header: true, size: small,
        align: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER })) }),
      ...b.rows.map((r) => new TableRow({ children: r.map((v, i) => cell(v, widths[i], { size: small,
        align: i > 0 && b.align === "right" ? AlignmentType.RIGHT : AlignmentType.LEFT })) })),
    ],
  });
}

const children = [];
for (const b of doc.blocks) {
  switch (b.type) {
    case "title":
      children.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun(b.text)] }));
      break;
    case "subtitle":
      children.push(new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: b.text, color: MUTED, size: 26 })] }));
      break;
    case "h1":
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(b.text)] }));
      break;
    case "h2":
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(b.text)] }));
      break;
    case "p":
      children.push(new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: b.text,
        italics: b.style === "note", color: b.style === "note" ? MUTED : undefined, size: b.style === "note" ? 20 : undefined })] }));
      break;
    case "bullets":
    case "numbers":
      for (const it of b.items) {
        children.push(new Paragraph({ numbering: { reference: b.type === "bullets" ? "bul" : "num", level: 0 },
          spacing: { after: 80 }, children: [new TextRun(it)] }));
      }
      break;
    case "table":
      children.push(table(b));
      children.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
      break;
    case "image": {
      const data = fs.readFileSync(b.path);
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 }, children: [
        new ImageRun({ type: "png", data, transformation: { width: b.w, height: b.h },
          altText: { title: b.alt, description: b.alt, name: path.basename(b.path) } })] }));
      break;
    }
    case "pagebreak":
      children.push(new Paragraph({ children: [new PageBreak()] }));
      break;
  }
}

const document = new Document({
  creator: "Uzbekistan Tourism Monitor",
  title: doc.title + " — " + doc.period,
  styles: {
    default: { document: { run: { font: "Times New Roman", size: 24, color: INK } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: "Times New Roman", size: 40, bold: true, color: INK },
        paragraph: { spacing: { after: 60 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Times New Roman", size: 30, bold: true, color: ACCENT },
        paragraph: { spacing: { before: 300, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Times New Roman", size: 26, bold: true, color: INK },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: "O'zbekiston turizm monitori · " + doc.period + " · ", size: 18, color: MUTED }),
      new TextRun({ children: [PageNumber.CURRENT], size: 18, color: MUTED })] })] }) },
    children,
  }],
});

Packer.toBuffer(document).then((buf) => {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  console.log("wrote", outPath);
});
