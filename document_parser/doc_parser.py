"""
DOC文件解析器
使用win32com读取Microsoft Word文档
"""
import os
import re
import tempfile
from typing import List, Dict, Optional
from .base_parser import BaseParser


class DOCParser(BaseParser):
    """DOC文档解析器（使用win32com）"""

    def __init__(self, file_path: Optional[str] = None, file_bytes: Optional[bytes] = None):
        """
        初始化解析器

        Args:
            file_path: 文件路径
            file_bytes: 文件字节数据
        """
        self.file_path = file_path
        self.file_bytes = file_bytes
        self.text: Optional[str] = None
        self.metadata: Dict = {}

        if file_bytes is not None:
            self._save_temp_file()

    def _save_temp_file(self):
        """将字节数据保存为临时文件"""
        if self.file_bytes is None:
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix='.doc') as tmp:
            tmp.write(self.file_bytes)
            self.file_path = tmp.name

    def parse(self) -> str:
        """
        解析文档并返回文本内容

        Returns:
            str: 解析后的文本内容
        """
        if self.text is not None:
            return self.text

        self.text = self._read_doc()
        return self.text

    def _read_doc(self) -> str:
        """
        使用win32com读取DOC文件

        Returns:
            str: 文档文本内容
        """
        if not self.file_path or not os.path.exists(self.file_path):
            return ""

        try:
            import win32com.client

            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False

            try:
                doc = word.Documents.Open(os.path.abspath(self.file_path))
                content = doc.Content.text
                doc.Close(False)
                return content
            finally:
                word.Quit()

        except Exception as e:
            return f"[错误]读取DOC文件失败: {str(e)}"

    def get_metadata(self) -> Dict[str, any]:
        """
        获取文档元数据

        Returns:
            Dict: 元数据字典
        """
        if not self.metadata and self.file_path:
            self.metadata = {
                "source": os.path.basename(self.file_path),
                "file_path": self.file_path,
                "file_size": os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0,
            }
        return self.metadata

    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的扩展名列表

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.doc']

    def extract_text(self) -> str:
        """
        提取纯文本内容

        Returns:
            str: 提取的文本内容
        """
        return self.parse()

    def extract_full_text(self) -> str:
        """
        提取完整文本（包含段落结构信息）

        Returns:
            str: 完整文本内容
        """
        if not self.file_path or not os.path.exists(self.file_path):
            return ""

        try:
            import win32com.client

            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False

            try:
                doc = word.Documents.Open(os.path.abspath(self.file_path))

                paragraphs = []
                for para in doc.Paragraphs:
                    text = para.Range.Text.strip()
                    if text:
                        paragraphs.append(text)

                doc.Close(False)
                return '\n'.join(paragraphs)
            finally:
                word.Quit()

        except Exception:
            return self.parse()

    def __del__(self):
        """清理临时文件"""
        if self.file_bytes is not None and self.file_path and os.path.exists(self.file_path):
            try:
                os.unlink(self.file_path)
            except:
                pass


def parse_doc_file(file_path: str) -> str:
    """
    解析DOC文件的便捷函数

    Args:
        file_path: 文件路径

    Returns:
        str: 解析后的文本内容
    """
    parser = DOCParser(file_path=file_path)
    return parser.parse()


def parse_doc_bytes(file_bytes: bytes, filename: str = "unknown.doc") -> str:
    """
    从字节数据解析DOC文件的便捷函数

    Args:
        file_bytes: 文件字节数据
        filename: 文件名

    Returns:
        str: 解析后的文本内容
    """
    parser = DOCParser(file_bytes=file_bytes)
    return parser.parse()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        parser = DOCParser(file_path=file_path)
        print(parser.parse())
    else:
        print("用法: python doc_parser.py <doc文件路径>")
