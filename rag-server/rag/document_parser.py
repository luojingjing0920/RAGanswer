from pathlib import Path

from pypdf import PdfReader
from docx import Document


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def parse_document(file_path: str) -> dict:
    """
    将不同格式文档解析为统一结构。

    返回格式：
    {
        "file_name": "...",
        "file_type": "pdf",
        "sections": [
            {
                "text": "...",
                "page": 1
            }
        ]
    }
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"暂不支持该文件类型: {suffix}"
        )

    if suffix == ".pdf":
        sections = _parse_pdf(path)

    elif suffix == ".docx":
        sections = _parse_docx(path)

    else:
        sections = _parse_text_file(path)

    # 去掉空文本
    sections = [
        section
        for section in sections
        if section["text"].strip()
    ]

    return {
        "file_name": path.name,
        "file_type": suffix.lstrip("."),
        "sections": sections
    }


def _parse_pdf(path: Path) -> list[dict]:
    """
    PDF 按页解析。

    保留 page 信息，后续引用溯源可以展示：
    xxx.pdf · 第3页
    """

    reader = PdfReader(str(path))

    sections = []

    for page_index, page in enumerate(
        reader.pages,
        start=1
    ):
        text = page.extract_text() or ""

        if text.strip():
            sections.append({
                "text": text.strip(),
                "page": page_index
            })

    return sections


def _parse_docx(path: Path) -> list[dict]:
    """
    DOCX 暂时按整个文档解析。

    DOCX 无法稳定获得真实页码，
    所以 page 使用 None。

    本质是流式排版文档
→ 页码会受到字体、页面尺寸、Word 渲染环境影响
    """

    document = Document(str(path))

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    full_text = "\n".join(paragraphs)

    if not full_text:
        return []

    return [{
        "text": full_text,
        "page": None
    }]


def _parse_text_file(path: Path) -> list[dict]:
    """
    TXT / Markdown 文本读取。
    """

    try:
        text = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:
        text = path.read_text(
            encoding="gb18030"
        )

    if not text.strip():
        return []

    return [{
        "text": text.strip(),
        "page": None
    }]
