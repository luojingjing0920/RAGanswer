def build_context(
    retrieval_results: list[dict]
) -> tuple[str, list[dict]]:
    """
    将 Retriever 返回的结果整理为 LLM Context，
    同时生成可供前端展示的 Source 信息。
    """

    context_parts = []
    sources = []

    for index, item in enumerate(
        retrieval_results,
        start=1
    ):
        metadata = item["metadata"]

        file_name = metadata.get(
            "file_name",
            "未知文件"
        )

        page = metadata.get("page")
        chunk_index = metadata.get(
            "chunk_index"
        )

        if page is not None:
            location = f"第 {page} 页"
        else:
            location = (
                f"片段 {chunk_index + 1}"
            )

        context_parts.append(
            f"""[资料 {index}]
文件：{file_name}
位置：{location}
内容：
{item["text"]}
"""
        )

        sources.append(
            {
                "source_id": index,
                "file_name": file_name,
                "page": page,
                "chunk_index": chunk_index,
                "similarity": item[
                    "similarity"
                ],
                "text": item["text"],
            }
        )

    context = "\n".join(
        context_parts
    )

    return context, sources
