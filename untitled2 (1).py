import streamlit as st
from transformers import pipeline
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import feedparser

# Page config
st.set_page_config(
    page_title="Finance News Dashboard",
    page_icon="📈",
    layout="wide"
)

# ------------------------
# 1. Setup (with caching)
# ------------------------
@st.cache_resource
def load_sentiment_model():
    """Load FinBERT model once and cache it"""
    return pipeline("sentiment-analysis", 
                   model="yiyanghkust/finbert-tone", 
                   tokenizer="yiyanghkust/finbert-tone")

# RSS feeds for Indian finance news
RSS_FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "Business Standard": "https://www.business-standard.com/rss/home_page_top_stories.rss",
    "LiveMint Markets": "https://www.livemint.com/rss/markets",
    "Financial Express": "https://www.financialexpress.com/market/rss"
}

finbert = load_sentiment_model()

def get_sentiment_finbert(text):
    """Get sentiment using FinBERT"""
    try:
        result = finbert(text[:512])[0]
        return result['label']
    except Exception as e:
        return "Neutral"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_finance_news():
    """Fetch and process finance news from RSS feeds"""
    all_articles = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, (source, url) in enumerate(RSS_FEEDS.items()):
        status_text.text(f"Fetching news from: {source}")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:  # Get top 10 from each source
                title = entry.get('title', '').strip()
                link = entry.get('link', '')
                published = entry.get('published', 'N/A')
                
                if title and link:
                    all_articles.append({
                        'title': title,
                        'source': source,
                        'link': link,
                        'published': published
                    })
        except Exception as e:
            st.warning(f"Error fetching from {source}: {str(e)}")
        
        progress_bar.progress((idx + 1) / len(RSS_FEEDS))
    
    progress_bar.empty()
    status_text.empty()
    
    # Remove duplicates by title
    unique_articles = {}
    for article in all_articles:
        if article['title'] not in unique_articles:
            unique_articles[article['title']] = article
    
    # Process articles and get sentiment
    data = []
    for article in list(unique_articles.values())[:30]:  # Top 30 articles
        sentiment = get_sentiment_finbert(article['title'])
        data.append({
            "Title": article['title'],
            "Source": article['source'],
            "Sentiment": sentiment,
            "Link": article['link']
        })
    
    return pd.DataFrame(data)

# ------------------------
# 2. Streamlit UI
# ------------------------
st.title("📈 Finance News Dashboard")
st.markdown("Real-time Indian finance news with sentiment analysis powered by FinBERT")
st.divider()

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    auto_refresh = st.checkbox("Auto-refresh (5 min)", value=False)
    sentiment_filter = st.multiselect(
        "Filter by Sentiment",
        ["Positive", "Negative", "Neutral"],
        default=["Positive", "Negative", "Neutral"]
    )
    st.divider()
    st.info("💡 Data refreshes every 5 minutes when cached")
    st.markdown("### 📰 News Sources")
    for source in RSS_FEEDS.keys():
        st.markdown(f"- {source}")

# Main content
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.metric("Data Source", "RSS Feeds")
with col2:
    st.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))
with col3:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Fetch news
with st.spinner("Fetching latest finance news..."):
    try:
        df = fetch_finance_news()
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        df = pd.DataFrame()

if df.empty:
    st.warning("No articles found. Try refreshing again.")
else:
    # Filter by sentiment
    df_filtered = df[df['Sentiment'].str.capitalize().isin(sentiment_filter)]
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Articles", len(df_filtered))
    with col2:
        positive_count = len(df_filtered[df_filtered['Sentiment'].str.lower() == 'positive'])
        st.metric("Positive", positive_count)
    with col3:
        negative_count = len(df_filtered[df_filtered['Sentiment'].str.lower() == 'negative'])
        st.metric("Negative", negative_count)
    with col4:
        neutral_count = len(df_filtered[df_filtered['Sentiment'].str.lower() == 'neutral'])
        st.metric("Neutral", neutral_count)
    
    st.divider()
    
    # Display articles
    for idx, row in df_filtered.iterrows():
        # Color based on sentiment
        if row['Sentiment'].lower() == 'positive':
            sentiment_color = "🟢"
            bg_color = "#d4edda"
        elif row['Sentiment'].lower() == 'negative':
            sentiment_color = "🔴"
            bg_color = "#f8d7da"
        else:
            sentiment_color = "🟡"
            bg_color = "#fff3cd"
        
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 15px; background-color: {bg_color}; border-radius: 5px; margin-bottom: 10px;">
                    <h4>{sentiment_color} {row['Title']}</h4>
                    <p style="color: #666; font-size: 14px;">
                        <b>Source:</b> {row['Source']} | <b>Sentiment:</b> {row['Sentiment']}
                    </p>
                    <a href="{row['Link']}" target="_blank" style="text-decoration: none;">
                        <button style="background-color: #0066cc; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                            Read Article →
                        </button>
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(300)  # 5 minutes
    st.rerun()
