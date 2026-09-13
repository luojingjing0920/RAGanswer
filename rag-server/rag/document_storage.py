import re
import shutil
from pathlib import Path


DOCUMENT_ID_PATTERN = re.compile(
    r"^[a-f0-9]{32}$"
)


class DocumentStorage:
    """
    原始文档持久化存储。

    目录结构：

    data/
    └── documents/
        └── {document_id}/
            └── original.pdf
    """

    def __init__(
        self,
        storage_dir: str | Path | None = None,
    ):
        if storage_dir is None:
            storage_dir = (
                Path(__file__).resolve()
                .parent.parent
                / "data"
                / "documents"
            )

        self.storage_dir = Path(storage_dir)

        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _validate_document_id(
        self,
        document_id: str,
    ) -> str:
        """
        校验 document_id。

        当前项目使用 uuid4().hex，
        因此 document_id 应为 32 位十六进制字符串。
        """

        document_id = document_id.strip().lower()

        if not DOCUMENT_ID_PATTERN.fullmatch(
            document_id
        ):
            raise ValueError(
                "非法的 document_id"
            )

        return document_id

    def _get_document_dir(
        self,
        document_id: str,
    ) -> Path:
        document_id = (
            self._validate_document_id(
                document_id
            )
        )

        return (
            self.storage_dir
            / document_id
        )

    def save(
        self,
        document_id: str,
        source_path: str | Path,
    ) -> Path:
        """
        保存原始上传文件。

        实际文件名统一为：

        original.<extension>

        不直接使用用户上传的文件名作为磁盘路径。
        """

        source_path = Path(source_path)

        if not source_path.exists():
            raise FileNotFoundError(
                f"源文件不存在：{source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"源路径不是文件：{source_path}"
            )

        suffix = source_path.suffix.lower()

        if not suffix:
            raise ValueError(
                "原始文档缺少文件扩展名"
            )

        document_dir = (
            self._get_document_dir(
                document_id
            )
        )

        document_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path = (
            document_dir
            / f"original{suffix}"
        )

        shutil.copy2(
            source_path,
            target_path,
        )

        return target_path

    def get(
        self,
        document_id: str,
    ) -> Path:
        """
        获取指定 document_id 对应的原始文件。
        """

        document_dir = (
            self._get_document_dir(
                document_id
            )
        )

        if not document_dir.exists():
            raise FileNotFoundError(
                "原始文档不存在"
            )

        files = list(
            document_dir.glob(
                "original.*"
            )
        )

        if not files:
            raise FileNotFoundError(
                "原始文档不存在"
            )

        if len(files) > 1:
            raise RuntimeError(
                "检测到多个原始文档文件"
            )

        return files[0]

    def delete(
        self,
        document_id: str,
    ) -> bool:
        """
        删除指定文档对应的整个存储目录。

        返回：
        True  -> 实际删除了目录
        False -> 原目录不存在
        """

        document_dir = (
            self._get_document_dir(
                document_id
            )
        )

        if not document_dir.exists():
            return False

        shutil.rmtree(
            document_dir
        )

        return True
