"""
法律文档解析器
解析《民法典》等法律文档，按"编-章-节-条"结构化提取
"""
import re
from typing import List, Dict, Optional
from .base_parser import BaseParser
from legal_entities import LegalDocument, LegalChapter, LegalProvision, ChapterLevel, DocumentType


class CivilLawParser(BaseParser):
    """《民法典》解析器"""

    def __init__(self, text: str, source: str = "unknown"):
        """
        初始化解析器

        Args:
            text: 文档文本内容
            source: 文档来源标识
        """
        self.text = text
        self.source = source
        self.chapters: List[LegalChapter] = []
        self.provisions: List[LegalProvision] = []

        self.chinese_num_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9
        }

    def parse(self) -> str:
        """
        解析文档并返回文本内容

        Returns:
            str: 解析后的文本内容
        """
        self._extract_structure()
        return self.text

    def get_metadata(self) -> Dict[str, any]:
        """
        获取文档元数据

        Returns:
            Dict: 元数据字典
        """
        return {
            "source": self.source,
            "total_chapters": len(self.chapters),
            "total_provisions": len(self.provisions),
            "document_type": "民法典",
        }

    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的扩展名列表

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return ['.txt', '.pdf']

    def get_structured_document(self) -> LegalDocument:
        """
        获取结构化的法律文档

        Returns:
            LegalDocument: 包含章节和条文完整信息的文档对象
        """
        if not self.provisions:
            self._extract_structure()

        return LegalDocument(
            document_id=self._generate_doc_id(),
            document_type=DocumentType.CIVIL_LAW,
            title="中华人民共和国民法典",
            issuing_authority="全国人民代表大会",
            issuing_date="2020-05-28",
            effective_date="2021-01-01",
            metadata=self.get_metadata(),
            provisions=self.provisions,
            chapters=self.chapters
        )

    def _extract_structure(self):
        """提取文档的章节和条文结构"""
        lines = self.text.split('\n')
        current_part = ""
        current_chapter = ""
        current_section = ""

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            if self._is_part_header(line):
                current_part = self._extract_part_name(line)
                chapter_code = self._generate_chapter_code("part", current_part)
                part_number = len([c for c in self.chapters if c.level == ChapterLevel.PART]) + 1
                chapter = LegalChapter(
                    level=ChapterLevel.PART,
                    code=chapter_code,
                    name=current_part,
                    full_name=f"第{part_number}编 {current_part}",
                    sort_order=part_number - 1
                )
                self.chapters.append(chapter)
                current_chapter = ""
                current_section = ""

            elif self._is_chapter_header(line):
                current_chapter = self._extract_chapter_name(line)
                parent_code = self.chapters[-1].code if self.chapters else None
                chapter_code = self._generate_chapter_code("chapter", current_chapter, parent_code)
                chapter = LegalChapter(
                    level=ChapterLevel.CHAPTER,
                    code=chapter_code,
                    name=current_chapter,
                    full_name=current_chapter,
                    parent_code=parent_code,
                    sort_order=len([c for c in self.chapters if c.level == ChapterLevel.CHAPTER])
                )
                self.chapters.append(chapter)
                current_section = ""

            elif self._is_section_header(line):
                current_section = self._extract_section_name(line)
                parent_code = self.chapters[-1].code if self.chapters else None
                chapter_code = self._generate_chapter_code("section", current_section, parent_code)
                chapter = LegalChapter(
                    level=ChapterLevel.SECTION,
                    code=chapter_code,
                    name=current_section,
                    full_name=current_section,
                    parent_code=parent_code,
                    sort_order=len([c for c in self.chapters if c.level == ChapterLevel.SECTION])
                )
                self.chapters.append(chapter)

            elif self._is_article_header(line):
                provision = self._parse_article(line, lines, i, current_part, current_chapter, current_section)
                if provision:
                    self.provisions.append(provision)

    def _is_part_header(self, line: str) -> bool:
        """判断是否为编标题"""
        patterns = [
            r'^第[一二三四五六七八九十百千]+编',
            r'^(第一编|第二编|第三编|第四编|第五编|第六编|第七编)\s',
        ]
        return any(re.match(pattern, line) for pattern in patterns)

    def _is_chapter_header(self, line: str) -> bool:
        """判断是否为章标题"""
        patterns = [
            r'^第[一二三四五六七八九十百千]+章',
            r'^(第一章|第二章|第三章|第四章|第五章|第六章|第七章|第八章|第九章|第十章)\s',
        ]
        return any(re.match(pattern, line) for pattern in patterns)

    def _is_section_header(self, line: str) -> bool:
        """判断是否为节标题"""
        patterns = [
            r'^第[一二三四五六七八九十百千\d]+节',
            r'^(第一节|第二节|第三节|第四节|第五节|第六节)\s',
        ]
        return any(re.match(pattern, line) for pattern in patterns)

    def _is_article_header(self, line: str) -> bool:
        """判断是否为条文标题"""
        pattern = r'^第[零一二三四五六七八九十百千\d]+条'
        return bool(re.match(pattern, line))

    def _extract_part_name(self, line: str) -> str:
        """提取编名称"""
        match = re.search(r'第[一二三四五六七八九十百千]+编\s*[「『]?(.+?)[」』]?$', line)
        return match.group(1).strip() if match else line.strip()

    def _extract_chapter_name(self, line: str) -> str:
        """提取章名称"""
        match = re.search(r'第[一二三四五六七八九十百千]+章\s*[「『]?(.+?)[」』]?$', line)
        return match.group(1).strip() if match else line.strip()

    def _extract_section_name(self, line: str) -> str:
        """提取节名称"""
        match = re.search(r'第[一二三四五六七八九十百千\d]+节\s*[「『]?(.+?)[」』]?$', line)
        return match.group(1).strip() if match else line.strip()

    def _parse_article(self, line: str, lines: List[str], index: int,
                       part: str, chapter: str, section: str) -> Optional[LegalProvision]:
        """
        解析条文内容

        Args:
            line: 当前行
            lines: 所有行
            index: 当前行索引
            part: 所属编
            chapter: 所属章
            section: 所属节

        Returns:
            LegalProvision: 解析出的条文对象
        """
        article_match = re.match(r'^第([零一二三四五六七八九十百千\d]+)条\s*(.*)$', line)
        if not article_match:
            return None

        num_str = article_match.group(1)
        article_number = str(self._chinese_to_arabic(num_str))
        content = article_match.group(2) if article_match.group(2) else ""

        j = index + 1
        while j < len(lines):
            next_line = lines[j].strip()
            if not next_line:
                j += 1
                continue
            if self._is_article_header(next_line):
                break
            if self._is_chapter_header(next_line):
                break
            if self._is_section_header(next_line):
                break
            if self._is_part_header(next_line):
                break
            content += ' ' + next_line
            j += 1

        if len(content.strip()) <= 5:
            return None

        return LegalProvision(
            article_id=self._generate_article_id(article_number),
            chapter=part or chapter,
            article_number=article_number,
            content=content.strip(),
            section=section if section else None,
            title=f"第{article_number}条",
            metadata={
                "part": part,
                "chapter": chapter,
                "section": section,
                "full_text": line + content
            }
        )

    def _chinese_to_arabic(self, chinese_str: str) -> int:
        """
        将中文数字转换为阿拉伯数字

        Args:
            chinese_str: 中文数字字符串

        Returns:
            int: 阿拉伯数字
        """
        if not chinese_str:
            return 0

        chinese_str = chinese_str.replace('零', '')

        if chinese_str == '十':
            return 10

        result = 0
        temp = 0
        i = 0

        while i < len(chinese_str):
            char = chinese_str[i]

            if char in self.chinese_num_map:
                temp = temp * 10 + self.chinese_num_map[char]
                i += 1
            elif char == '十':
                if i == 0:
                    result += 10
                else:
                    result += temp * 10
                temp = 0
                i += 1
            elif char == '百':
                result += temp * 100
                temp = 0
                i += 1
            elif char == '千':
                result += temp * 1000
                temp = 0
                i += 1
            elif char == '万':
                result = (result + temp) * 10000
                temp = 0
                i += 1
            else:
                i += 1

        result += temp
        return result

    def _generate_chapter_code(self, level: str, name: str, parent_code: Optional[str] = None) -> str:
        """生成章节代码"""
        prefix_map = {
            "part": "P",
            "chapter": "C",
            "section": "S"
        }
        prefix = prefix_map.get(level, "X")
        name_hash = str(abs(hash(name)))[-6:]
        return f"{prefix}{name_hash}"

    def _generate_article_id(self, article_number: str) -> str:
        """生成条文ID"""
        return f"ART{article_number.zfill(4)}"

    def _generate_doc_id(self) -> str:
        """生成文档ID"""
        return "CIVIL_LAW_2021"

    def get_provisions_by_chapter(self, chapter_code: str) -> List[LegalProvision]:
        """获取指定章节的所有条文"""
        return [
            p for p in self.provisions
            if p.metadata.get('chapter') == chapter_code
        ]

    def get_provisions_by_section(self, section_name: str) -> List[LegalProvision]:
        """获取指定节的所有条文"""
        return [
            p for p in self.provisions
            if p.metadata.get('section') == section_name
        ]

    def search_provisions(self, keyword: str) -> List[LegalProvision]:
        """搜索包含关键词的条文"""
        keyword_lower = keyword.lower()
        return [
            p for p in self.provisions
            if keyword_lower in p.content.lower()
        ]


def parse_civil_law_text(text: str, source: str = "unknown") -> CivilLawParser:
    """
    解析法律文档文本的便捷函数

    Args:
        text: 文档文本
        source: 文档来源

    Returns:
        CivilLawParser: 解析器实例
    """
    parser = CivilLawParser(text, source)
    parser.parse()
    return parser


if __name__ == '__main__':
    sample_text = """
第一编 总则
第一章 基本规定
第一条 为了保护民事主体的合法权益，调整民事关系，维护社会和经济秩序，适应中国特色社会主义发展要求，弘扬社会主义核心价值观，根据宪法，制定本法。
第二条 民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。

第一千二百五十九条 民法所称的“以上”、“以下”、“以内”、“届满”，包括本数；所称的“不满”、“超过”、“以外”、“不满”，不包括本数。
第一千二百六十条 本法自2021年1月1日起施行。
    """

    parser = parse_civil_law_text(sample_text, "sample")
    doc = parser.get_structured_document()

    print(f"文档类型: {doc.document_type}")
    print(f"章节数: {len(doc.chapters)}")
    print(f"条文数: {len(doc.provisions)}")
    print("\n章节列表:")
    for chapter in doc.chapters:
        print(f"  [{chapter.level.value}] {chapter.full_name}")
    print("\n条文示例:")
    for prov in doc.provisions[:3]:
        print(f"  第{prov.article_number}条: {prov.content[:50]}...")
