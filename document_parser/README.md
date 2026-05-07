# 📄 文档解析器模块

本模块提供多格式文档解析功能，包括 PDF 解析、Word 文档解析、法律文档解析和裁判文书解析。

## 模块结构

```
document_parser/
├── __init__.py          # 包初始化，导出主要类和函数
├── base_parser.py       # 解析器基类，定义统一接口
├── factory.py           # 解析器工厂，根据文件类型选择解析器
├── pdf_parser.py       # PDF 文档解析器
├── doc_parser.py       # Word 文档解析器 (DOC/DOCX)
├── legal_parser.py      # 《民法典》解析器
└── case_parser.py      # 裁判文书解析器
```

## 主要功能

### 1. PDF 文档解析 (pdf_parser.py)

使用 PyMuPDF (fitz) 库提取 PDF 文本内容。

**主要类**: `PDFParser`

**功能**:
- `extract_text()` - 提取 PDF 所有文本
- `extract_metadata()` - 提取元数据（标题、作者、页数等）
- `get_text_by_page()` - 按页提取文本
- `extract_images_info()` - 提取图片信息
- `extract_tables()` - 提取表格（实验性）

**使用示例**:
```python
from document_parser import PDFParser

with PDFParser("document.pdf") as parser:
    text = parser.extract_text()
    metadata = parser.extract_metadata()
    print(f"标题: {metadata['title']}")
    print(f"页数: {metadata['total_pages']}")
```

### 2. Word 文档解析 (doc_parser.py)

使用 win32com 接口调用 Microsoft Word 读取 DOC/DOCX 文件。

**主要类**: `DOCParser`

**功能**:
- `parse()` - 解析文档文本
- `get_metadata()` - 获取文档元数据
- `extract_text()` - 提取纯文本内容

**使用示例**:
```python
from document_parser import DOCParser

parser = DOCParser(file_path="document.doc")
text = parser.parse()
print(f"文档长度: {len(text)} 字符")
```

**注意事项**:
- 需要 Windows 系统
- 需要安装 Microsoft Word
- DOC 格式使用 Microsoft Word 97-2003
- DOCX 格式使用 Office Open XML

### 3. 《民法典》解析器 (legal_parser.py)

专门用于解析《中华人民共和国民法典》，提取"编-章-节-条"结构。

**主要类**: `CivilLawParser`

**功能**:
- `parse()` - 解析文档文本
- `get_structured_document()` - 获取结构化文档对象
- `get_provisions_by_chapter()` - 按章节获取条文
- `search_provisions()` - 搜索条文

**数据结构**:
- `LegalDocument` - 完整的法律文档对象
- `LegalChapter` - 章节信息（编/章/节）
- `LegalProvision` - 条文信息

**使用示例**:
```python
from document_parser import CivilLawParser, parse_civil_law_text

# 方法1: 使用类
parser = CivilLawParser(text, source="文件名")
parser.parse()
doc = parser.get_structured_document()

print(f"章节数: {len(doc.chapters)}")
print(f"条文数: {len(doc.provisions)}")

# 方法2: 使用便捷函数
parser = parse_civil_law_text(text, "民法典")
```

### 4. 裁判文书解析器 (case_parser.py)

解析法院判决书、裁定书等裁判文书。

**主要类**: `CaseParser`

**功能**:
- `parse()` - 解析文书文本
- `get_structured_case()` - 获取结构化案例对象
- `extract_case_number()` - 提取案号
- `extract_case_type()` - 提取案件类型
- `extract_issues()` - 提取争议焦点
- `extract_applied_provisions()` - 提取适用法条

**数据结构**:
- `CaseAnalysis` - 完整的案例分析对象

**使用示例**:
```python
from document_parser import CaseParser, parse_case_text

# 方法1: 使用类
parser = CaseParser(text, source="判决书.pdf")
parser.parse()
case = parser.get_structured_case()

print(f"案号: {case.case_number}")
print(f"争议焦点: {case.issues}")
print(f"适用法条: {case.applied_provisions}")

# 方法2: 使用便捷函数
parser = parse_case_text(text, "sample_case")
```

### 5. 解析器工厂 (factory.py)

根据文件类型自动选择合适的解析器。

**主要类**: `DocumentParserFactory`

**功能**:
- `get_parser()` - 根据文件扩展名获取解析器
- `register_parser()` - 注册新的解析器
- `is_supported()` - 检查是否支持该文件类型
- `get_supported_extensions()` - 获取支持的扩展名列表

**使用示例**:
```python
from document_parser import DocumentParserFactory

factory = DocumentParserFactory()
parser = factory.get_parser("document.pdf")
text = parser.extract_text()
```

## 支持的文件格式

| 格式 | 解析器 | 状态 | 说明 |
|------|--------|------|------|
| PDF | PDFParser | ✅ 完整支持 | 使用 PyMuPDF |
| DOC | DOCParser | ✅ 完整支持 | 使用 win32com |
| DOCX | DOCParser | ✅ 完整支持 | 使用 win32com |
| TXT | PDFParser | ✅ 完整支持 | 纯文本读取 |
| 《民法典》 | CivilLawParser | ✅ 完整支持 | 结构化解析 |
| 裁判文书 | CaseParser | ✅ 完整支持 | 案例分析 |

## 数据结构

### LegalChapter (章节)

```python
@dataclass
class LegalChapter:
    level: ChapterLevel          # 章节级别（编/章/节）
    code: str                    # 章节代码
    name: str                    # 章节名称
    full_name: str               # 完整名称
    parent_code: Optional[str]    # 父章节代码
    sort_order: int              # 排序序号
```

### LegalProvision (条文)

```python
@dataclass
class LegalProvision:
    article_id: str               # 条文ID
    chapter: str                  # 所属章节
    article_number: str          # 条文编号
    content: str                 # 条文内容
    section: Optional[str]        # 所属节
    title: Optional[str]         # 条文标题
    related_provisions: List[str] # 相关法条
    keywords: List[str]          # 关键词
```

### CaseAnalysis (案例分析)

```python
@dataclass
class CaseAnalysis:
    case_id: str                 # 案例ID
    case_number: str             # 案号
    title: str                    # 案件标题
    case_type: str                # 案件类型
    court_level: str             # 审理法院级别
    judgment_date: str           # 裁判日期
    facts: str                   # 案件事实
    reasoning: str               # 裁判理由
    judgment_result: str         # 裁判结果
    issues: List[str]            # 争议焦点
    applied_provisions: List[str]# 适用法条
    key_points: List[str]       # 裁判要旨
```

## 扩展解析器

如果要添加新的文档格式解析器，请继承 `BaseParser` 类：

```python
from document_parser import BaseParser

class MyCustomParser(BaseParser):
    def parse(self) -> str:
        # 实现解析逻辑
        pass

    def get_metadata(self) -> Dict[str, any]:
        # 返回元数据
        pass

    def get_supported_extensions(self) -> List[str]:
        # 返回支持的扩展名
        return ['.myformat']
```

然后在 `factory.py` 中注册：

```python
factory = DocumentParserFactory()
factory.register_parser('.myformat', MyCustomParser)
```

## 注意事项

1. **中文数字转换**: 解析器支持中文数字（十、百、千、万）和阿拉伯数字的转换
2. **编码问题**: 确保文本文件使用 UTF-8 编码
3. **PDF 限制**: 只能提取文本型 PDF，扫描版 PDF 需要 OCR 处理
4. **Word 限制**: 需要 Windows 系统和 Microsoft Word
5. **大文件**: 对于大型文档，建议分批处理以避免内存问题

## 依赖

- PyMuPDF (fitz) - PDF 解析
- win32com (pywin32) - Word 文档解析
- Python 3.8+
- re (标准库)
- typing (标准库)

## 许可证

本项目采用 MIT 许可证。
