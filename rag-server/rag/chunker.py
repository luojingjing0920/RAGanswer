def chunk_document(
    document: dict,
    chunk_size: int = 500,
    overlap: int = 100
) -> list[dict]:
    """
    将解析后的文档切分为多个重叠 chunk。

    document:
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

    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    if overlap < 0:
        raise ValueError("overlap 不能小于 0")

    if overlap >= chunk_size:
        raise ValueError(
            "overlap 必须小于 chunk_size"
        )

    chunks = []
    chunk_index = 0

    sections = document.get("sections", [])

    for section_index, section in enumerate(sections):
        text = section.get("text", "").strip()
        page = section.get("page")

        if not text:
            continue

        start = 0

        while start < len(text):
            end = min(
                start + chunk_size,
                len(text)
            )

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_index": chunk_index,
                    "section_index": section_index,
                    "file_name": document["file_name"],
                    "file_type": document["file_type"],
                    "page": page,
                    "start_char": start,
                    "end_char": end,
                    "text": chunk_text
                })

                chunk_index += 1

            # 已经到正文末尾
            if end >= len(text):
                break

            # 下一块向前重叠 overlap 个字符
            start = end - overlap

    return chunks

