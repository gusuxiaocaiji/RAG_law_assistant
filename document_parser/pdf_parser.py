"""
PDF文档解析器
使用 PyMuPDF (fitz) 实现 PDF 文本提取和元数据获取
"""
import fitz
import io
from typing import List, Dict, Optional
from datetime import datetime


class PDFParser:
    def __init__(self, file_path: Optional[str] = None, file_bytes: Optional[bytes] = None):
        """
        初始化PDF解析器
        
        Args:
            file_path: PDF文件路径
            file_bytes: PDF文件字节数据（二选一）
        """
        if file_path:
            self.doc = fitz.open(file_path)
            self.source = file_path
        elif file_bytes:
            self.doc = fitz.open(stream=file_bytes, filetype="pdf")
            self.source = "memory_stream"
        else:
            raise ValueError("必须提供 file_path 或 file_bytes")

    def extract_text(self) -> str:
        """
        提取PDF所有文本内容
        
        Returns:
            str: 提取的文本内容
        """
        text_parts = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"[页{page_num + 1}]\n{text}")
        
        return "\n\n".join(text_parts) if text_parts else ""

    def extract_metadata(self) -> Dict[str, any]:
        """
        提取PDF元数据
        
        Returns:
            Dict: 包含标题、作者、页数等信息的字典
        """
        metadata = self.doc.metadata
        
        result = {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "total_pages": len(self.doc),
            "source": self.source,
            "extract_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return result

    def get_text_by_page(self) -> List[Dict[str, any]]:
        """
        获取每页的文本内容
        
        Returns:
            List[Dict]: 每页包含页码和文本的列表
        """
        pages_data = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()
            
            pages_data.append({
                "page_number": page_num + 1,
                "text": text,
                "word_count": len(text),
            })
        
        return pages_data

    def extract_images_info(self) -> List[Dict[str, any]]:
        """
        提取PDF中嵌入图片的信息
        
        Returns:
            List[Dict]: 图片信息列表
        """
        images = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = self.doc.extract_image(xref)
                
                images.append({
                    "page": page_num + 1,
                    "index": img_index + 1,
                    "xref": xref,
                    "width": base_image.get("width", 0),
                    "height": base_image.get("height", 0),
                    "colorspace": base_image.get("colorspace", ""),
                    "bpc": base_image.get("bpc", 0),
                    "size": len(base_image.get("image", b"")),
                })
        
        return images

    def extract_tables(self, page_numbers: Optional[List[int]] = None) -> Dict[int, List[str]]:
        """
        提取PDF中的表格（实验性功能）
        
        Args:
            page_numbers: 指定页码列表，为None则提取所有页
            
        Returns:
            Dict[int, List[str]]: 每页的表格文本列表
        """
        tables = {}
        pages_to_check = page_numbers if page_numbers else range(len(self.doc))
        
        for page_num in pages_to_check:
            if page_num >= len(self.doc):
                continue
                
            page = self.doc[page_num]
            text = page.get_text()
            
            page_tables = []
            lines = text.split('\n')
            
            current_table = []
            in_table = False
            
            for line in lines:
                if self._is_table_row(line):
                    in_table = True
                    current_table.append(line)
                elif in_table and line.strip():
                    if current_table:
                        page_tables.append('\t'.join(current_table))
                        current_table = []
                    in_table = False
            
            if current_table:
                page_tables.append('\t'.join(current_table))
            
            tables[page_num] = page_tables
        
        return tables

    def _is_table_row(self, line: str) -> bool:
        """
        判断文本行是否为表格行
        
        Args:
            line: 文本行
            
        Returns:
            bool: 是否为表格行
        """
        if not line or len(line.strip()) < 3:
            return False
        
        separators = ['\t', '|', '  ']
        count = sum(line.count(sep) for sep in separators)
        
        return count >= 2

    def close(self):
        """关闭PDF文档"""
        if hasattr(self, 'doc'):
            self.doc.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_page_count(self) -> int:
        """获取PDF页数"""
        return len(self.doc)

    def is_encrypted(self) -> bool:
        """检查PDF是否加密"""
        return self.doc.is_encrypted


def parse_pdf(file_path: str) -> Dict[str, any]:
    """
    解析PDF文件的便捷函数
    
    Args:
        file_path: PDF文件路径
        
    Returns:
        Dict: 包含文本和元数据的字典
    """
    with PDFParser(file_path) as parser:
        return {
            "text": parser.extract_text(),
            "metadata": parser.extract_metadata(),
            "pages": parser.get_text_by_page(),
        }


def parse_pdf_bytes(file_bytes: bytes) -> Dict[str, any]:
    """
    从字节数据解析PDF的便捷函数
    
    Args:
        file_bytes: PDF文件字节数据
        
    Returns:
        Dict: 包含文本和元数据的字典
    """
    with PDFParser(file_bytes=file_bytes) as parser:
        return {
            "text": parser.extract_text(),
            "metadata": parser.extract_metadata(),
            "pages": parser.get_text_by_page(),
        }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        
        print(f"正在解析: {pdf_path}")
        print("=" * 60)
        
        result = parse_pdf(pdf_path)
        
        print(f"标题: {result['metadata']['title']}")
        print(f"作者: {result['metadata']['author']}")
        print(f"页数: {result['metadata']['total_pages']}")
        print("=" * 60)
        print(f"前500字符内容预览:")
        print(result['text'][:500])
    else:
        print("用法: python pdf_parser.py <pdf文件路径>")