"""
document_parser - 多格式文档解析模块

支持以下文档格式：
- PDF: 使用 PyMuPDF (fitz)
- 法律文档: 解析《民法典》等法律原文
- 裁判文书: 解析判决书、裁定书等
- (更多格式将陆续添加)
"""
from .base_parser import BaseParser
from .factory import DocumentParserFactory, parse_document
from .pdf_parser import PDFParser
from .legal_parser import CivilLawParser, parse_civil_law_text
from .case_parser import CaseParser, parse_case_text
from .doc_parser import DOCParser, parse_doc_file, parse_doc_bytes

__all__ = [
    'BaseParser',
    'DocumentParserFactory',
    'parse_document',
    'PDFParser',
    'CivilLawParser',
    'parse_civil_law_text',
    'CaseParser',
    'parse_case_text',
    'DOCParser',
    'parse_doc_file',
    'parse_doc_bytes',
]