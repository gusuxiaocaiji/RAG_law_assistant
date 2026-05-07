import streamlit as st
import config_data as config
from vector_stores import VectorStoresService
from langchain_community.embeddings import DashScopeEmbeddings

st.set_page_config(
    page_title="法条检索",
    page_icon="📖",
    layout="wide"
)


if "vector_store" not in st.session_state:
    st.session_state["vector_store"] = VectorStoresService(
        embedding=DashScopeEmbeddings(model=config.embedding_model_name)
    )


if "current_part" not in st.session_state:
    st.session_state["current_part"] = None

if "current_chapter" not in st.session_state:
    st.session_state["current_chapter"] = None

if "current_section" not in st.session_state:
    st.session_state["current_section"] = None


st.title("📖 民法典法条检索")
st.caption("按编、章、节结构浏览或精确搜索法条")

col_search, col_browse = st.columns(2)

with col_search:
    st.subheader("🔍 精确搜索")

    search_mode = st.radio(
        "搜索方式",
        options=["article_number", "concept", "range"],
        format_func=lambda x: {
            "article_number": "📌 按法条编号",
            "concept": "🌐 按法律概念",
            "range": "📊 按条文范围"
        }[x],
        horizontal=True
    )

    if search_mode == "article_number":
        article_input = st.text_input(
            "输入法条编号",
            placeholder="例如：123、第一百二十三条",
            help="支持阿拉伯数字（123）或中文数字（第一百二十三条）"
        )

        if st.button("搜索法条", type="primary"):
            if article_input:
                with st.spinner("检索中..."):
                    try:
                        results = st.session_state["vector_store"].search_by_article_number(
                            article_input,
                            max_results=5
                        )
                        st.session_state["search_results"] = results
                        st.session_state["display_mode"] = "search"
                    except Exception as e:
                        st.error(f"搜索出错: {str(e)}")

    elif search_mode == "concept":
        concept_input = st.text_input(
            "输入法律概念",
            placeholder="例如：合同、侵权、债权",
            help="输入您想了解的法律概念"
        )

        if st.button("搜索概念", type="primary"):
            if concept_input:
                with st.spinner("检索中..."):
                    try:
                        results = st.session_state["vector_store"].search_by_concept(
                            concept_input,
                            max_results=10
                        )
                        st.session_state["search_results"] = results
                        st.session_state["display_mode"] = "search"
                    except Exception as e:
                        st.error(f"搜索出错: {str(e)}")

    else:
        col_start, col_end = st.columns(2)
        with col_start:
            start_article = st.number_input("起始条文", min_value=1, max_value=1260, value=1)
        with col_end:
            end_article = st.number_input("结束条文", min_value=1, max_value=1260, value=100)

        if st.button("检索范围", type="primary"):
            with st.spinner("检索中..."):
                try:
                    results = st.session_state["vector_store"].search_by_provisions_range(
                        start_article,
                        end_article,
                        max_results=50
                    )
                    st.session_state["search_results"] = results
                    st.session_state["display_mode"] = "search"
                except Exception as e:
                    st.error(f"搜索出错: {str(e)}")

with col_browse:
    st.subheader("🌳 章节浏览")

    civil_law_structure = {
        "第一编 总则": [
            "第一章 基本规定",
            "第二章 自然人",
            "第三章 法人",
            "第四章 非法人组织",
            "第五章 民事权利",
            "第六章 民事法律行为",
            "第七章 代理"
        ],
        "第二编 物权": [
            "第一分编 通则",
            "第二分编 所有权",
            "第三分编 用益物权",
            "第四分编 担保物权"
        ],
        "第三编 合同": [
            "第一分编 通则",
            "第二分编 典型合同",
            "第三分编 准合同"
        ],
        "第四编 人格权": [
            "第一章 一般规定",
            "第二章 生命权、身体权和健康权",
            "第三章 姓名权和名称权",
            "第四章 肖像权",
            "第五章 名誉权和荣誉权",
            "第六章 隐私权和个人信息保护"
        ],
        "第五编 婚姻家庭": [
            "第一章 一般规定",
            "第二章 结婚",
            "第三章 家庭关系",
            "第四章 离婚",
            "第五章 收养"
        ],
        "第六编 继承": [
            "第一章 一般规定",
            "第二章 法定继承",
            "第三章 遗嘱继承和遗赠",
            "第四章 遗产的处理"
        ],
        "第七编 侵权责任": [
            "第一章 一般规定",
            "第二章 损害赔偿",
            "第三章 责任主体的特殊规定",
            "第四章 产品责任",
            "第五章 机动车交通事故责任",
            "第六章 医疗损害责任",
            "第七章 环境污染和生态破坏责任",
            "第八章 高度危险责任",
            "第九章 饲养动物损害责任",
            "第十章 建筑物和物件损害责任"
        ]
    }

    for part, chapters in civil_law_structure.items():
        with st.expander(part):
            for chapter in chapters:
                btn_key = f"btn_{part}_{chapter}"
                if st.button(f"📚 {chapter}", key=btn_key):
                    with st.spinner("加载中..."):
                        try:
                            results = st.session_state["vector_store"].search_by_chapter(
                                part=part,
                                chapter=chapter,
                                max_results=20
                            )
                            st.session_state["search_results"] = results
                            st.session_state["display_mode"] = "browse"
                            st.session_state["current_part"] = part
                            st.session_state["current_chapter"] = chapter
                            st.rerun()
                        except Exception as e:
                            st.error(f"加载出错: {str(e)}")

st.divider()


if "search_results" in st.session_state and st.session_state["search_results"]:
    results = st.session_state["search_results"]
    display_mode = st.session_state.get("display_mode", "search")

    if display_mode == "browse" and st.session_state.get("current_chapter"):
        st.subheader(f"📖 {st.session_state['current_part']} - {st.session_state['current_chapter']}")
    else:
        st.subheader(f"📋 搜索结果 ({len(results)} 条)")

    tab_list, tab_content = st.tabs([f"法条 {i+1}" for i in range(min(len(results), 10))])

    for i, (tab, doc) in enumerate(zip(tab_list, results)):
        with tab:
            metadata = doc.metadata

            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**📌 条文编号**: 第 {metadata.get('article_number', 'N/A')} 条")
                st.markdown(f"**📂 所属编**: {metadata.get('part', '未知')}")

            with col_info2:
                st.markdown(f"**📑 章节**: {metadata.get('chapter', '未知')}")
                section = metadata.get('section', '')
                if section:
                    st.markdown(f"**📁 节**: {section}")

            st.divider()

            st.markdown("**📜 法条内容**")
            st.markdown(doc.page_content)

            with st.expander("🔗 引用关系分析"):
                st.markdown("**相关法律概念**")
                concepts = metadata.get('legal_concepts', [])
                if concepts:
                    for concept in concepts[:5]:
                        st.markdown(f"- {concept}")
                else:
                    st.info("暂无概念标签")

                st.markdown("**引用本条的司法解释**")
                related_docs = metadata.get('related_provisions', [])
                if related_docs:
                    for related in related_docs[:5]:
                        st.markdown(f"- {related}")
                else:
                    st.info("暂无关联司法解释")

            with st.expander("💡 法条解读"):
                st.markdown("""
                **适用场景**
                本条主要涉及民事法律关系中的相关问题，适用于...

                **构成要件**
                1. 要件一：...
                2. 要件二：...

                **法律效果**
                满足上述要件后，将产生以下法律效果...
                """)
                st.caption("提示：具体解读请参考司法解释和权威著述")

    if len(results) > 10:
        st.info(f"共找到 {len(results)} 条结果，仅显示前 10 条。请使用精确搜索查看特定法条。")

else:
    st.info("👈 请通过左侧搜索或章节浏览选择法条")

    with st.expander("📚 民法典结构概览"):
        st.markdown("""
        ## 《民法典》七编结构

        | 编 | 名称 | 主要内容 |
        |-----|------|----------|
        | **第一编** | 总则 | 基本规定、自然人、法人、民事权利、法律行为、代理 |
        | **第二编** | 物权 | 所有权、用益物权、担保物权 |
        | **第三编** | 合同 | 合同通则、典型合同、准合同 |
        | **第四编** | 人格权 | 生命权、姓名权、肖像权、隐私权等 |
        | **第五编** | 婚姻家庭 | 结婚、家庭关系、离婚、收养 |
        | **第六编** | 继承 | 法定继承、遗嘱继承、遗产处理 |
        | **第七编** | 侵权责任 | 损害赔偿、各类侵权责任 |

        **条文总数**: 1260 条
        """)

        st.markdown("""
        ### 💡 使用提示

        1. **精确搜索**: 输入法条编号（如"123"或"第一百二十三条"）快速定位
        2. **概念搜索**: 输入法律概念（如"合同"、"侵权"）查找相关法条
        3. **范围检索**: 指定起始和结束条文编号，批量查看
        4. **章节浏览**: 通过编-章-节结构逐级浏览法条
        """)