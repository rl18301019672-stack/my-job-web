import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# === 1. 网页基础设置 ===
st.set_page_config(
    page_title="校招情报局", 
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 2026 校招/实习情报局")
st.markdown("""
这里是你的个人情报中心。点击左侧的 **“开始抓取”** 按钮，系统会自动从 *GiveMeOC* 获取最新岗位。
""")

# === 2. 核心爬虫功能 (这就是刚才你写的那个爬虫) ===
def run_spider(max_pages):
    base_url = "http://www.givemeoc.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    all_data = []
    current_url = base_url
    
    # 创建一个进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for page in range(1, max_pages + 1):
        status_text.text(f"正在扫描第 {page}/{max_pages} 页...")
        progress_bar.progress(page / max_pages)
        
        try:
            response = requests.get(current_url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                rows = soup.find_all('tr')
                
                for row in rows[1:]:
                    try:
                        cols = row.find_all('td')
                        if len(cols) >= 11:
                            # --- 链接清洗逻辑 ---
                            apply_link = "无链接"
                            apply_col = cols[10].find('a')
                            if apply_col and 'href' in apply_col.attrs:
                                raw_href = apply_col['href'].strip()
                                # 修复脏数据
                                if "链接投递" in raw_href:
                                    raw_href = raw_href.replace("链接投递", "").replace(":", "").replace("：", "").strip()
                                try:
                                    apply_link = urljoin(base_url, raw_href)
                                except:
                                    apply_link = "链接错误"
                            
                            info = {
                                "公司": cols[0].text.strip(),
                                "投递直达": apply_link, # 放在前面方便点
                                "岗位": cols[6].text.strip(),
                                "地点": cols[5].text.strip(),
                                "截止日期": cols[9].text.strip(),
                                "类型": cols[3].text.strip(),
                                "行业": cols[2].text.strip(),
                                "发布时间": cols[8].text.strip()
                            }
                            all_data.append(info)
                    except:
                        continue
                
                # 寻找下一页
                next_page_found = False
                all_links = soup.find_all('a')
                for link in all_links:
                    if "下一页" in link.text or "»" in link.text:
                        next_url = link.get('href')
                        if next_url:
                            current_url = urljoin(base_url, next_url)
                            next_page_found = True
                            break
                
                if not next_page_found:
                    st.warning("已到达最后一页")
                    break
            else:
                st.error(f"第 {page} 页访问失败")
                
        except Exception as e:
            st.error(f"发生错误: {e}")
            break
            
    progress_bar.empty() # 抓完后隐藏进度条
    status_text.text("✅ 抓取完成！")
    return pd.DataFrame(all_data)

# === 3. 侧边栏控制区 ===
with st.sidebar:
    st.header("🎮 控制台")
    pages_to_crawl = st.slider("抓取多少页？", 1, 50, 5) # 默认抓5页
    
    if st.button("🚀 开始抓取数据", type="primary"):
        with st.spinner('正在疯狂爬取中，请稍等...'):
            df = run_spider(pages_to_crawl)
            # 把数据存到 session_state 里，这样刷新网页数据不会丢
            st.session_state['data'] = df
            st.success(f"成功获取 {len(df)} 条岗位信息！")

# === 4. 数据展示区 ===
if 'data' in st.session_state:
    df = st.session_state['data']
    
    # 简单的筛选器
    search_term = st.text_input("🔍 搜索公司或岗位 (例如: 腾讯 / Java)", "")
    if search_term:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
    
    # 展示漂亮的表格，链接可点击
    st.dataframe(
        df,
        column_config={
            "投递直达": st.column_config.LinkColumn("点击投递"),
        },
        use_container_width=True,
        height=600
    )
    
    # 下载按钮
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "💾 下载为 Excel/CSV",
        csv,
        "校招数据.csv",
        "text/csv",
        key='download-csv'
    )
else:
    st.info("👈 请在左侧侧边栏设置页数，并点击按钮开始抓取。")
