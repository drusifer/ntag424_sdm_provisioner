# Enhanced PDF Extraction Guide

## Overview

The enhanced PDF extractor (`pdf_to_markdown_extractor.py`) converts PDFs to markdown with intelligent content analysis and enhanced features:

- **Text extraction** for PDFs with extractable text
- **OCR support** for image-based PDFs  
- **Inline SVG embedding** for Cursor compatibility (no separate SVG files)
- **Mermaid diagram generation** for flowcharts and processes
- **Markdown table conversion** for tabular data
- **PNG image extraction** as fallback option

## Usage

### Basic Usage

```bash
# Extract with inline SVG (default - Cursor-friendly)
python pdf_to_markdown_extractor.py document.pdf

# Extract with custom output name
python pdf_to_markdown_extractor.py document.pdf my-document

# Extract as PNG images instead of inline SVG
python pdf_to_markdown_extractor.py document.pdf --no-inline-svg
```

### Installation Dependencies

```bash
# Install extraction dependencies
pip install -e .[extraction]

# Or install manually
pip install PyMuPDF Pillow pytesseract
```

**Note:** For OCR functionality, you'll also need Tesseract installed on your system:
- Windows: Download from GitHub releases
- macOS: `brew install tesseract`
- Ubuntu: `sudo apt install tesseract-ocr`

## Features Explained

### Inline SVG vs PNG Extraction

**Inline SVG (Default - Recommended for Cursor):**
- Embeds vector graphics directly in markdown
- No separate files to manage
- Scalable and crisp at any zoom level
- Cursor-friendly (no SVG file issues)

**PNG Extraction (Fallback):**
- Creates separate PNG files in `images/` directory
- Better for complex images with many details
- Use `--no-inline-svg` flag

### Intelligent Content Detection

The extractor automatically detects and handles:

1. **Text Content**: Extractable text from PDFs
2. **OCR Requirements**: Image-based PDFs requiring text recognition
3. **Tables**: Converts to markdown table format
4. **Diagrams**: Generates mermaid diagrams for:
   - Flowcharts and processes
   - Sequence diagrams
   - Architecture diagrams

### Output Structure

Generated markdown includes:

```markdown
# Document Title

- **Author:** Document Author
- **Total Pages:** XX
- **Extraction Method:** Text + OCR + Inline SVG
- **Enhanced Features:** Mermaid diagrams, Markdown tables, Inline SVG

---

## Page 1

### Extracted Text
[Clean, formatted text content]

### Tables
[Markdown tables converted from PDF]

### Diagrams
[Mermaid diagrams generated from content]

### Page Content (Inline SVG)
[Full page as embedded SVG when appropriate]

---
```

## Examples

### Technical Documentation
```bash
# Extract datasheet with inline SVG
python pdf_to_markdown_extractor.py nxp-ntag424-datasheet.pdf ntag424-enhanced
```

### API Documentation  
```bash
# Extract API reference
python pdf_to_markdown_extractor.py API-ACR122U-2.04.pdf acr122u-reference
```

### Research Papers
```bash
# Extract with PNG images for complex diagrams
python pdf_to_markdown_extractor.py research-paper.pdf paper-analysis --no-inline-svg
```

## Best Practices

1. **Use inline SVG** for most documents (Cursor compatibility)
2. **Use PNG extraction** only for very complex visual content
3. **Name your outputs** meaningfully for better organization
4. **Check OCR results** for image-based PDFs and manually correct if needed

## Command Line Integration

The extractor is available as a command-line tool after installation:

```bash
# Install in development mode
pip install -e .

# Use the extract-pdf command
extract-pdf document.pdf output-name
```

## Troubleshooting

### OCR Not Working
- Install tesseract: `brew install tesseract` (macOS) or `sudo apt install tesseract-ocr` (Ubuntu)
- Check pytesseract installation: `pip install pytesseract`

### Large SVG Content
- Use `--no-inline-svg` for very large documents
- Inline SVG may slow down markdown rendering for huge files

### Poor Text Extraction
- Try OCR mode by ensuring images are present in the PDF
- Some PDFs have text as images requiring OCR

## Integration with Current Workflow

This enhanced extractor replaces the previous SVG-file-based approach:

- ✅ **Before**: PDF → Multiple SVG files (Cursor issues)
- ✅ **Now**: PDF → Single markdown with inline SVG (Cursor-friendly)

Perfect for documentation workflows where you need searchable, navigable content without file management overhead.
