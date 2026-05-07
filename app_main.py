import streamlit as st

st.set_page_config(
    page_title="法律助手",
    page_icon="⚖️",
    layout="wide"
)


st.title("⚖️ 民事法律助手")
st.caption("基于《民法典》的智能法律辅助系统")

st.divider()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    ### 📚 知识库更新
    上传《民法典》原文、判决文书等法律文档，构建专业知识库
    """)

with col2:
    st.markdown("""
    ### 💬 智能问答
    基于RAG技术，智能解答《民法典》相关法律问题
    """)

with col3:
    st.markdown("""
    ### 📖 法条检索
    按编、章、节结构浏览或精确搜索法条
    """)

with col4:
    st.markdown("""
    ### ⚖️ 案例分析
    输入案情描述，获取案件要素分析和相关案例
    """)

st.divider()

st.markdown("""
## 🚀 使用指南

请使用左侧导航栏访问各个功能模块：

- **📚 知识库更新** - 上传和管理法律文档
- **💬 智能问答** - 与法律助手对话
- **📖 法条检索** - 搜索和浏览《民法典》法条
- **⚖️ 案例分析** - 分析案情并获取相关案例
""")

with st.expander("ℹ️ 系统说明"):
    st.markdown("""
    本系统基于《中华人民共和国民法典》，提供以下核心功能：

    1. **混合检索**：结合向量检索和关键词检索，提供更准确的检索结果
    2. **类案推送**：根据当前问题自动推荐相关案例
    3. **章节导航**：按照民法典的编、章、节结构浏览法条
    4. **智能问答**：基于RAG技术理解用户问题并提供准确回答

    ### 技术架构
    - **前端**：Streamlit 多页面应用
    - **后端**：RAG（检索增强生成）系统
    - **向量数据库**：ChromaDB
    - **Embedding模型**：DashScope 文字嵌入模型
    - **大语言模型**：通义千问（Qwen）
    """)
