"""
文档解析器工厂类
根据文件类型自动选择合适的解析器
"""
import os
from typing import Optional
from .pdf_parser import PDFParser
from .doc_parser import DOCParser


class DocumentParserFactory:
    """文档解析器工厂"""
    
    def __init__(self):
        self.parsers = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """注册默认的解析器"""
        self.parsers['.pdf'] = PDFParser
        self.parsers['.doc'] = DOCParser
        self.parsers['.docx'] = PDFParser
    
    def register_parser(self, extension: str, parser_class):
        """
        注册新的解析器
        
        Args:
            extension: 文件扩展名（如 '.pdf'）
            parser_class: 解析器类
        """
        self.parsers[extension.lower()] = parser_class
    
    def get_parser(self, file_path: str, file_bytes: Optional[bytes] = None):
        """
        根据文件类型获取对应的解析器
        
        Args:
            file_path: 文件路径
            file_bytes: 文件字节数据（可选）
            
        Returns:
            对应的解析器实例
            
        Raises:
            ValueError: 不支持的文件类型
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext not in self.parsers:
            supported = ', '.join(self.parsers.keys())
            raise ValueError(f"不支持的文件类型: {ext}。支持的类型: {supported}")
        
        parser_class = self.parsers[ext]
        
        if file_bytes:
            return parser_class(file_bytes=file_bytes)
        else:
            return parser_class(file_path=file_path)
    
    def get_supported_extensions(self) -> list:
        """
        获取所有支持的扩展名
        
        Returns:
            list: 支持的文件扩展名列表
        """
        return list(self.parsers.keys())
    
    def is_supported(self, file_path: str) -> bool:
        """
        检查文件类型是否支持
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否支持
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.parsers


def parse_document(file_path: str, file_bytes: Optional[bytes] = None) -> dict:
    """
    解析文档的便捷函数
    
    Args:
        file_path: 文件路径
        file_bytes: 文件字节数据（可选）
        
    Returns:
        dict: 包含文本和元数据的字典
    """
    factory = DocumentParserFactory()
    parser = factory.get_parser(file_path, file_bytes)
    
    return {
        "text": parser.extract_text() if hasattr(parser, 'extract_text') else parser.parse(),
        "metadata": parser.extract_metadata() if hasattr(parser, 'extract_metadata') else parser.get_metadata(),
    }


if __name__ == '__main__':
    factory = DocumentParserFactory()
    
    print("支持的文档类型:", factory.get_supported_extensions())
    print("PDF支持状态:", factory.is_supported("test.pdf"))
    print("TXT支持状态:", factory.is_supported("test.txt"))