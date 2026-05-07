"""
知识库
"""
import hashlib
import os.path
import json
import re
import config_data as config
from typing import List, Dict, Optional
from datetime import datetime
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from document_parser.pdf_parser import PDFParser
from document_parser.doc_parser import DOCParser
from document_parser.factory import DocumentParserFactory
from legal_entities import DocumentType, LegalProvision, LegalChapter, CaseAnalysis, ChapterLevel
from legal_graph import LegalKnowledgeGraph

load_dotenv(verbose=True)

def check_md5(md5_str: str):
    """检查传入的md5字符串是否已经被处理过了"""
    if not os.path.exists(config.md5_path):
        open(config.md5_path, 'w',encoding='utf-8').close()
        return False

    else:
        for line in open(config.md5_path, 'r', encoding='utf-8').readlines():
            line = line.strip()
            if line == md5_str:
                return True

        return False


def save_md5(md5_str: str):
    """将传入的md5字符串保存到文件夹中"""
    with open(config.md5_path, 'a', encoding='utf-8') as f:
        f.write(md5_str + '\n')


def get_str_md5(input_str: str, encoding='utf-8'):
    """将传入的字符串转换为md5字符串"""
    str_bytes = input_str.encode(encoding=encoding)
    md5_obj = hashlib.md5()
    md5_obj.update(str_bytes)
    md5_hex = md5_obj.hexdigest()
    return md5_hex


class KnowledgeBaseService(object):
    def __init__(self):
        os.makedirs(config.persist_directory, exist_ok=True)

        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=DashScopeEmbeddings(model='text-embedding-v4'),
            persist_directory=config.persist_directory,
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,
        )
        
        self.legal_graph = LegalKnowledgeGraph()
        self._init_legal_graph()

    def _init_legal_graph(self):
        """初始化或加载法律知识图谱"""
        graph_path = os.path.join(config.persist_directory, 'legal_graph')
        if os.path.exists(f"{graph_path}_provisions.gml"):
            try:
                self.legal_graph.load_graph(graph_path)
            except Exception:
                self.legal_graph = LegalKnowledgeGraph()

    def upload_by_str(self, data: str, filename, metadata: Optional[Dict] = None):
        """将传入的字符串，进行向量化，存入向量数据库中"""
        md5hex = get_str_md5(data)

        if check_md5(md5hex):
            return "[跳过]内容已存在知识库中"

        if len(data) > config.max_split_char_number:
            knowledge_chunks = self.spliter.split_text(data)
        else:
            knowledge_chunks = [data]

        default_metadata = {
            "source": filename,
            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "operator": "麦麦",
        }
        if metadata:
            default_metadata.update(metadata)

        self.chroma.add_texts(
            knowledge_chunks,
            metadatas=[default_metadata for _ in knowledge_chunks],
        )

        save_md5(md5hex)

        return "[成功]内容已成功载入向量库"

    def upload_legal_provisions(self, provisions: List[LegalProvision], chapters: List[LegalChapter] = None):
        """
        专门处理法条上传
        
        Args:
            provisions: 法律条文列表
            chapters: 编章节结构列表
            
        Returns:
            str: 处理结果信息
        """
        try:
            if chapters:
                for chapter in chapters:
                    self.legal_graph.add_chapter(chapter)
            
            for provision in provisions:
                self.legal_graph.add_provision(provision)
                
                metadata = {
                    "source": f"民法典第{provision.article_number}条",
                    "doc_type": DocumentType.CIVIL_LAW.value,
                    "article_id": provision.article_id,
                    "article_number": provision.article_number,
                    "chapter": provision.chapter,
                    "section": provision.section or "",
                    "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                
                self.upload_by_str(provision.content, f"民法典_{provision.article_number}", metadata)
            
            graph_path = os.path.join(config.persist_directory, 'legal_graph')
            self.legal_graph.save_graph(graph_path)
            
            return f"[成功]已成功导入 {len(provisions)} 条法律条文"
            
        except Exception as e:
            return f"[错误]处理法条数据失败: {str(e)}"

    def upload_case_data(self, cases: List[CaseAnalysis]):
        """
        处理案例数据上传
        
        Args:
            cases: 案例分析列表
            
        Returns:
            str: 处理结果信息
        """
        try:
            for case in cases:
                metadata = {
                    "source": case.case_number,
                    "doc_type": DocumentType.JUDGMENT.value,
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "case_type": case.case_type,
                    "court_level": case.court_level,
                    "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                
                case_text = f"""
                案件标题：{case.title}
                案号：{case.case_number}
                案件类型：{case.case_type}
                法院层级：{case.court_level}
                裁判日期：{case.judgment_date}
                
                案件事实：
                {case.facts}
                
                争议焦点：
                {'；'.join(case.issues)}
                
                适用法条：
                {'；'.join(case.applied_provisions)}
                
                裁判结果：
                {case.judgment_result}
                
                裁判要旨：
                {case.reasoning}
                """
                
                self.upload_by_str(case_text, f"案例_{case.case_number}", metadata)
            
            return f"[成功]已成功导入 {len(cases)} 个案例"
            
        except Exception as e:
            return f"[错误]处理案例数据失败: {str(e)}"

    def upload_legal_document(self, file_bytes: bytes, filename: str, doc_type: DocumentType):
        """
        根据文档类型路由到不同解析器
        
        Args:
            file_bytes: 文件字节数据
            filename: 文件名
            doc_type: 文档类型
            
        Returns:
            str: 处理结果信息
        """
        if doc_type == DocumentType.CIVIL_LAW:
            return self._process_civil_law(file_bytes, filename)
        elif doc_type == DocumentType.JUDGMENT:
            return self._process_judgment(file_bytes, filename)
        else:
            return self._process_general(file_bytes, filename)

    def _process_civil_law(self, file_bytes: bytes, filename: str) -> str:
        """
        处理民法典文档
        
        Args:
            file_bytes: 文件字节数据
            filename: 文件名
            
        Returns:
            str: 处理结果信息
        """
        try:
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.pdf':
                with PDFParser(file_bytes=file_bytes) as parser:
                    text = parser.extract_text()
            else:
                text = file_bytes.decode('utf-8', errors='ignore')
            
            if not text or len(text.strip()) == 0:
                return "[警告]文档中没有提取到文本内容"
            
            provisions = self._parse_provisions(text)
            chapters = self._parse_chapters(text)
            self._extract_references(provisions, text)
            
            return self.upload_legal_provisions(provisions, chapters)
            
        except Exception as e:
            return f"[错误]处理民法典文档失败: {str(e)}"

    def _process_judgment(self, file_bytes: bytes, filename: str) -> str:
        """
        处理判决文书
        
        Args:
            file_bytes: 文件字节数据
            filename: 文件名
            
        Returns:
            str: 处理结果信息
        """
        try:
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.pdf':
                with PDFParser(file_bytes=file_bytes) as parser:
                    text = parser.extract_text()
            elif ext == '.doc':
                doc_parser = DOCParser(file_bytes=file_bytes)
                text = doc_parser.parse()
                del doc_parser
            elif ext == '.docx':
                doc_parser = DOCParser(file_bytes=file_bytes)
                text = doc_parser.parse()
                del doc_parser
            else:
                text = file_bytes.decode('utf-8', errors='ignore')
            
            if not text or len(text.strip()) == 0:
                return "[警告]文档中没有提取到文本内容"
            
            case = self._parse_case(text, filename)
            return self.upload_case_data([case])
            
        except Exception as e:
            return f"[错误]处理判决文书失败: {str(e)}"

    def _process_general(self, file_bytes: bytes, filename: str) -> str:
        """
        处理通用文档
        
        Args:
            file_bytes: 文件字节数据
            filename: 文件名
            
        Returns:
            str: 处理结果信息
        """
        try:
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.pdf':
                with PDFParser(file_bytes=file_bytes) as parser:
                    text = parser.extract_text()
                    metadata = parser.extract_metadata()
                    return self.upload_by_str(text, metadata.get('title') or filename)
            elif ext == '.doc':
                doc_parser = DOCParser(file_bytes=file_bytes)
                text = doc_parser.parse()
                del doc_parser
                return self.upload_by_str(text, filename)
            elif ext == '.docx':
                doc_parser = DOCParser(file_bytes=file_bytes)
                text = doc_parser.parse()
                del doc_parser
                return self.upload_by_str(text, filename)
            else:
                text = file_bytes.decode('utf-8', errors='ignore')
                return self.upload_by_str(text, filename)
                
        except Exception as e:
            return f"[错误]处理文件失败: {str(e)}"

    def _parse_provisions(self, text: str) -> List[LegalProvision]:
        """
        解析法律条文

        Args:
            text: 文档文本

        Returns:
            List[LegalProvision]: 法律条文列表
        """
        provisions = []

        text = re.sub(r'\[页\d+\]', '', text)
        lines = text.split('\n')

        current_part = ""
        current_chapter = ""
        current_section = ""

        chinese_num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                          '六': 6, '七': 7, '八': 8, '九': 9}

        def chinese_to_arabic(chinese_str: str) -> int:
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
                if char in chinese_num_map:
                    temp = temp * 10 + chinese_num_map[char]
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

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            part_match = re.match(r'^第([一二三四五六七八九十百零\d]+)编\s*(.+)$', line)
            if part_match:
                current_part = part_match.group(2).strip()[:50]
                current_chapter = ""
                current_section = ""
                continue

            chapter_match = re.match(r'^第([一二三四五六七八九十百零\d]+)章\s*(.+)$', line)
            if chapter_match:
                current_chapter = chapter_match.group(2).strip()[:50]
                current_section = ""
                continue

            section_match = re.match(r'^第([一二三四五六七八九十百零\d]+)节\s*(.+)$', line)
            if section_match:
                current_section = section_match.group(2).strip()[:50]
                continue

            article_match = re.match(r'^第([零一二三四五六七八九十百千\d]+)条\s*(.*)$', line)
            if article_match:
                num_str = article_match.group(1)
                article_num_arabic = str(chinese_to_arabic(num_str))
                content = article_match.group(2) if article_match.group(2) else ""

                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    if re.match(r'^第[零一二三四五六七八九十百千\d]+条', next_line):
                        break
                    content += ' ' + next_line
                    j += 1

                if len(content.strip()) > 5:
                    provision = LegalProvision(
                        article_id=f"civil_law_{article_num_arabic}",
                        chapter=current_chapter or current_part,
                        section=current_section if current_section else None,
                        article_number=article_num_arabic,
                        content=content[:2000],
                    )
                    provisions.append(provision)

        return provisions

    def _parse_chapters(self, text: str) -> List[LegalChapter]:
        """
        解析编章节结构
        
        Args:
            text: 文档文本
            
        Returns:
            List[LegalChapter]: 编章节列表
        """
        chapters = []
        
        part_pattern = r'第([一二三四五六七八九十百零\d]+)编\s*(.+?)(?=\n第[一二三四五六七八九十百零\d]+编|$)'
        chapter_pattern = r'第([一二三四五六七八九十百零\d]+)章\s*(.+?)(?=\n第[一二三四五六七八九十百零\d]+章|$)'
        section_pattern = r'第([一二三四五六七八九十百零\d]+)节\s*(.+?)(?=\n第[一二三四五六七八九十百零\d]+节|$)'
        
        for match in re.finditer(part_pattern, text):
            order = self._chinese_to_arabic(match.group(1))
            chapters.append(LegalChapter(
                level=ChapterLevel.PART,
                code=f"part_{order}",
                name=match.group(2).strip()[:50],
                full_name=f"第{match.group(1)}编 {match.group(2).strip()[:50]}",
                sort_order=order * 10000
            ))
        
        for match in re.finditer(chapter_pattern, text):
            order = self._chinese_to_arabic(match.group(1))
            chapters.append(LegalChapter(
                level=ChapterLevel.CHAPTER,
                code=f"chapter_{order}",
                name=match.group(2).strip()[:50],
                full_name=f"第{match.group(1)}章 {match.group(2).strip()[:50]}",
                sort_order=order * 100
            ))
        
        for match in re.finditer(section_pattern, text):
            order = self._chinese_to_arabic(match.group(1))
            chapters.append(LegalChapter(
                level=ChapterLevel.SECTION,
                code=f"section_{order}",
                name=match.group(2).strip()[:50],
                full_name=f"第{match.group(1)}节 {match.group(2).strip()[:50]}",
                sort_order=order
            ))
        
        return chapters

    def _parse_case(self, text: str, filename: str) -> CaseAnalysis:
        """
        解析判决文书
        
        Args:
            text: 文档文本
            filename: 文件名
            
        Returns:
            CaseAnalysis: 案例分析对象
        """
        case_number_match = re.search(r'((20\d{2})[\u4e00-\u9fa5]\d+号)', text)
        case_number = case_number_match.group(1) if case_number_match else filename
        
        title_match = re.search(r'([^（\n]+)', text[:200])
        title = title_match.group(1).strip() if title_match else filename
        
        court_match = re.search(r'(最高人民法院|高级人民法院|中级人民法院|基层人民法院)', text)
        court = court_match.group(1) if court_match else "未知法院"
        
        case_type_match = re.search(r'(民事|刑事|行政|执行)案件', text)
        case_type = case_type_match.group(1) if case_type_match else "民事"
        
        date_pattern = r'(20\d{2})年(\d{1,2})月(\d{1,2})日'
        date_match = re.search(date_pattern, text)
        judgment_date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}" if date_match else "2020-01-01"
        
        provision_pattern = r'第(\d+)条'
        provisions = list(set([f"第{m.group(1)}条" for m in re.finditer(provision_pattern, text)]))[:20]
        
        return CaseAnalysis(
            case_id=get_str_md5(case_number)[:16],
            case_number=case_number,
            title=title[:100],
            case_type=case_type,
            court_level=court,
            judgment_date=judgment_date,
            facts=text[:1000],
            issues=["争议焦点待分析"],
            applied_provisions=provisions,
            reasoning=text[:1500],
            judgment_result="裁判结果待提取",
        )

    def _extract_references(self, provisions: List[LegalProvision], text: str):
        """
        提取条文引用关系
        
        Args:
            provisions: 法律条文列表
            text: 文档文本
        """
        ref_pattern = r'第(\d+)条'
        all_refs = set()
        
        for m in re.finditer(ref_pattern, text):
            ref_num = m.group(1)
            for provision in provisions:
                if provision.article_number != ref_num:
                    all_refs.add((provision.article_id, f"civil_law_{ref_num}"))
        
        from legal_entities import ArticleReference, ReferenceType
        
        for source_id, target_id in all_refs:
            ref = ArticleReference(
                source_article_id=source_id,
                target_article_id=target_id,
                reference_type=ReferenceType.CITATION,
            )
            self.legal_graph.add_reference(ref)

    def _chinese_to_arabic(self, chinese: str) -> int:
        """将中文数字转换为阿拉伯数字"""
        chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '零': 0}
        try:
            return int(chinese) if chinese.isdigit() else chinese_nums.get(chinese, 0)
        except:
            return 0

    def upload_by_pdf(self, file_path: str):
        """将PDF文件解析并导入知识库"""
        try:
            with PDFParser(file_path) as parser:
                text = parser.extract_text()
                metadata = parser.extract_metadata()
                
                if not text or len(text.strip()) == 0:
                    return "[警告]PDF文件中没有提取到文本内容"
                
                return self.upload_by_str(text, metadata.get('title') or os.path.basename(file_path))
                
        except Exception as e:
            return f"[错误]处理PDF文件失败: {str(e)}"

    def upload_by_file(self, file_path: str):
        """根据文件类型自动选择解析器上传到知识库"""
        try:
            factory = DocumentParserFactory()
            
            if not factory.is_supported(file_path):
                return f"[错误]不支持的文件类型: {os.path.splitext(file_path)[1]}"
            
            parser = factory.get_parser(file_path)
            text = parser.extract_text()
            
            if not text or len(text.strip()) == 0:
                return "[警告]文件中没有提取到文本内容"
            
            metadata = parser.extract_metadata()
            return self.upload_by_str(text, metadata.get('title') or os.path.basename(file_path))
            
        except Exception as e:
            return f"[错误]处理文件失败: {str(e)}"
        
    def upload_by_file_bytes(self, file_bytes: bytes, filename: str):
        """根据文件字节数据上传到知识库"""
        try:
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.pdf':
                with PDFParser(file_bytes=file_bytes) as parser:
                    text = parser.extract_text()
                    metadata = parser.extract_metadata()
                    
                    if not text or len(text.strip()) == 0:
                        return "[警告]PDF文件中没有提取到文本内容"
                    
                    return self.upload_by_str(text, metadata.get('title') or filename)
            else:
                text = file_bytes.decode('utf-8', errors='ignore')
                return self.upload_by_str(text, filename)
                
        except Exception as e:
            return f"[错误]处理文件失败: {str(e)}"


if __name__ == '__main__':
    service = KnowledgeBaseService()
    r = service.upload_by_str("周杰伦333", "testfile")
    print(r)
