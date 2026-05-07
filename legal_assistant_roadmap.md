# 《民法典》法律助手 - 代码改造实施路线图

本文档记录将现有 RAG 客服系统改造为《民法典》法律助手的具体代码实施步骤。

***

## 步骤1：环境准备与依赖安装

### 1.1 安装法律领域相关依赖

```bash
pip install -U langchain-community langchain-chroma pymupdf
pip install networkx matplotlib  # 用于知识图谱可视化
```

### 1.2 创建法律数据结构体

新建文件：`legal_entities.py`

```python
# 定义法律条文、案例等数据结构体
# 包含编章节层级、法条引用关系等字段定义
```

### 1.3 配置法律领域参数

修改文件：`config_data.py`

```python
# 更新向量数据库配置
collection_name = 'civil_law'
chunk_size = 500  # 法条较短，减少块大小
chunk_overlap = 50

# 新增法律专用配置
legal_max_results = 5  # 检索返回结果数
enable_citation = True  # 启用法条引用
```

### 1.4 创建知识图谱基础类

新建文件：`legal_graph.py`

```python
# 使用 networkx 构建法律条文关系图谱
# 实现法条引用关系存储和查询
```

***

## 步骤2：核心模块改造

### 2.1 扩展法律数据结构体

修改文件：`legal_entities.py`

新增文档类型枚举：

```python
class DocumentType(Enum):
    CIVIL_LAW = "民法典"
    JUDGMENT = "判决文书"
    GENERAL = "通用文档"
```

### 2.2 重构知识库服务

修改文件：`knowledge_base.py`

- 实现 `upload_by_str()` 方法支持结构化法条数据
- 新增 `upload_legal_document()` 方法，支持文档类型路由：
  ```python
  def upload_legal_document(self, file_bytes: bytes, filename: str, doc_type: DocumentType):
      # 根据文档类型路由到不同解析器
      if doc_type == DocumentType.CIVIL_LAW:
          return self._process_civil_law(file_bytes, filename)
      elif doc_type == DocumentType.JUDGMENT:
          return self._process_judgment(file_bytes, filename)
      else:
          return self._process_general(file_bytes, filename)
  ```
- 新增 `upload_legal_provisions()` 专门处理法条上传
- 新增 `upload_case_data()` 处理案例数据上传
- 实现条文引用关系提取和存储
- 添加法条元数据（编、章、节、条号、款数）

### 2.3 扩展文件上传器功能

修改文件：`app_file_uploader.py`

新增文档类型选择和路由逻辑：

```python
from knowledge_base import KnowledgeBaseService
from legal_entities import DocumentType

st.title("知识库更新服务")

# 新增文档类型选择
doc_type = st.selectbox(
    "选择文档类型",
    ["通用文档", "《民法典》原文", "判决文书"]
)

# 文件上传逻辑保持不变
uploader_file = st.file_uploader(
    "请上传文件",
    type=['txt', 'pdf'],
    accept_multiple_files=False,
)

# 根据类型调用不同上传方法
if doc_type == "《民法典》原文":
    result = st.session_state["service"].upload_legal_document(
        file_bytes, file_name, DocumentType.CIVIL_LAW
    )
elif doc_type == "判决文书":
    result = st.session_state["service"].upload_legal_document(
        file_bytes, file_name, DocumentType.JUDGMENT
    )
else:
    # 原有通用文档处理逻辑
    if ext == '.pdf':
        result = st.session_state["service"].upload_by_file_bytes(file_bytes, file_name)
    else:
        text = file_bytes.decode("utf-8")
        result = st.session_state["service"].upload_by_str(text, file_name)
```

### 2.4 新建法律文档解析器

新建文件：`document_parser/legal_parser.py`

```python
# 解析《民法典》PDF/TXT 原文
# 按"编-章-节-条"结构化提取
# 自动识别条文编号和条款内容
```

### 2.5 新建案例解析器

新建文件：`document_parser/case_parser.py`

```python
# 解析裁判文书结构
# 提取案由、争议焦点、裁判要旨
# 识别适用法条组合
```

### 2.6 重构向量检索服务 ✅

修改文件：`vector_stores.py`

- ✅ 新增 `search_by_article_number()` 按法条编号精确检索
- ✅ 新增 `search_by_concept()` 按法律概念语义检索
- ✅ 新增 `search_by_doc_type()` 按文档类型检索
- ✅ 实现混合检索策略（向量 + 关键词）
- ✅ 添加元数据过滤（按编、章、案由等）
- ✅ 新增 `search_by_chapter()` 按章节检索
- ✅ 新增 `search_by_provisions_range()` 按条文范围检索

**实现文件**:

- [vector\_stores.py](file:///d:/agent_learning/RAGProject/vector_stores.py) - 核心向量检索服务
- [VECTOR\_SEARCH\_API.md](file:///d:/agent_learning/RAGProject/VECTOR_SEARCH_API.md) - API 文档
- [test\_vector\_stores.py](file:///d:/agent_learning/RAGProject/test_vector_stores.py) - 测试脚本

### 2.7 重构 RAG 核心逻辑 ✅

修改文件：`rag.py`

- ✅ 更新提示词模板，适配法律回答规范
- ✅ 新增法条引用格式化函数
- ✅ 实现多轮对话中的法律关系追踪
- ✅ 添加案例推送逻辑
- ✅ 根据文档来源动态选择提示词模板

**实现类**:

- `LegalRAGService` - 法律助手 RAG 服务（主服务）
- `LegalCitationFormatter` - 法条引用格式化器
- `LegalRelationTracker` - 法律关系追踪器
- `CasePushService` - 案例推送服务
- `PromptTemplateManager` - 提示词模板管理器

***

## 步骤3：前端界面改造

### 3.1 新建法律助手主界面

修改文件：`app_qa.py`

- 改造成法律助手对话界面
- 添加法条展示卡片
- 新增案例推荐展示
- 添加追问引导按钮

### 3.2 新建法条检索界面

新建文件：`app_articles.py`

- 实现按编章节浏览法条
- 支持法条编号精确搜索
- 展示法条解读和引用关系

### 3.3 新建案例分析界面

新建文件：`app_cases.py`

- 案情输入框
- 案件要素提取展示
- 适用法条列表
- 类案推送结果

### 3.4 更新对话历史存储

修改文件：`file_history_store.py`

```python
# 新增法律对话状态结构
# 记录当前讨论的法律关系类型
# 追踪已确认适用的法条
```

***

## 步骤4：数据准备与导入

### 4.1 准备《民法典》原始数据

获取《民法典》全文数据（1260条）

```bash
# 创建数据目录
mkdir -p data/legal_provisions
mkdir -p data/cases
mkdir -p data/interpretations
```

### 4.2 处理法条数据

```bash
python -m document_parser.legal_parser data/legal_provisions/civil_law.txt
```

### 4.3 导入法条到知识库

方式一：通过文件上传界面导入

```python
# 用户直接在 app_file_uploader.py 中选择"《民法典》原文"上传
```

方式二：程序化导入

```python
from knowledge_base import KnowledgeBaseService

service = KnowledgeBaseService()
service.upload_legal_provisions('data/legal_provisions/structured.json')
```

### 4.4 导入案例数据（如有）

方式一：通过文件上传界面导入

```python
# 用户直接在 app_file_uploader.py 中选择"判决文书"上传
```

方式二：程序化导入

```python
service.upload_case_data('data/cases/formatted_cases.json')
```

***

## 步骤5：系统集成与测试

### 5.1 配置多页面应用

修改文件：`app_main.py`

```python
# 使用 Streamlit 多页面功能整合
# 导航栏：知识库更新 | 智能问答 | 法条检索 | 案例分析
```

### 5.2 功能测试清单

- [ ] 法条编号精确检索测试
- [ ] 法律概念语义检索测试
- [ ] 智能问答法条引用测试
- [ ] 多轮对话法律关系追踪测试
- [ ] 类案推送准确性测试
- [ ] 《民法典》原文上传解析测试
- [ ] 判决文书上传解析测试
- [ ] 文档类型路由正确性测试

### 5.3 启动应用

```bash
streamlit run app_main.py
```

***

## 步骤6：持续优化

### 6.1 法律专用词向量微调（如条件允许）

```python
# 使用法律语料微调 DashScope embedding
# 提升法律术语理解能力
```

### 6.2 知识图谱完善

```python
# 补充司法解释关联
# 添加典型案例标注
# 完善条文引用关系
```

### 6.3 回答质量优化

- 根据用户反馈调整提示词模板
- 优化检索结果重排序策略
- 添加法律风险评估模块

***

## 附录1：文件结构规划

```
RAGProject/
├── legal_entities.py              # [新建] 法律数据结构体（含DocumentType枚举）
├── legal_graph.py                 # [新建] 知识图谱基础类
├── knowledge_base.py              # [修改] 知识库服务（支持文档类型路由）
├── vector_stores.py               # [修改] 向量检索服务
├── rag.py                         # [修改] RAG 核心逻辑
├── app_main.py                    # [新建] 多页面主入口
├── app_qa.py                      # [修改] 法律问答界面
├── app_file_uploader.py          # [修改] 知识库更新界面（新增文档类型选择）
├── app_articles.py                # [新建] 法条检索界面
├── app_cases.py                   # [新建] 案例分析界面
├── document_parser/
│   ├── __init__.py              # [新建] 包初始化
│   ├── legal_parser.py         # [新建] 法条解析器
│   └── case_parser.py          # [新建] 案例解析器
└── data/
    ├── legal_provisions/         # 法条原始数据
    └── cases/                    # 案例数据
```

***

## 附录2：文档处理流程

```
用户上传文档
     │
     ▼
┌─────────────────────────────────────┐
│  app_file_uploader.py              │
│  - 文件类型选择（通用/民法典/判决书）│
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  KnowledgeBaseService              │
│  - upload_legal_document()         │
│  - 识别文档类型路由                 │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  根据类型分发到对应解析器          │
│  - 民法典 → legal_parser.py        │
│  - 判决书 → case_parser.py         │
│  - 其他 → 原有处理逻辑            │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  数据结构化 & 存入向量数据库       │
└─────────────────────────────────────┘
```

***

**说明**：以上为技术路线文档，具体代码实现需根据实际法条数据格式和业务需求进行调整。
