import streamlit as st
import pandas as pd
from datetime import datetime
import feedparser
from textblob import TextBlob
import re

# Page config
st.set_page_config(
    page_title="Finance News Dashboard",
    page_icon="📈",
    layout="wide"
)

# RSS feeds for Indian finance news
RSS_FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "Business Standard": "https://www.business-standard.com/rss/home_page_top_stories.rss",
    "LiveMint Markets": "https://www.livemint.com/rss/markets",
    "Financial Express": "https://www.financialexpress.com/market/rss"
}

# Finance-specific sentiment keywords
POSITIVE_WORDS = [
    'gain', 'gains', 'surge', 'surges', 'rally', 'rallies', 'jump', 'jumps',
    'rise', 'rises', 'up', 'high', 'higher', 'record', 'profit', 'profits',
    'growth', 'positive', 'strong', 'beat', 'beats', 'outperform', 'soar',
    'boost', 'advance', 'advances', 'bullish', 'upgrade', 'upgrades'
]

NEGATIVE_WORDS = [
    'fall', 'falls', 'drop', 'drops', 'decline', 'declines', 'plunge', 'plunges',
    'down', 'low', 'lower', 'loss', 'losses', 'weak', 'miss', 'misses',
    'underperform', 'crash', 'slump', 'bearish', 'downgrade', 'downgrades',
    'slide', 'slides', 'tumble', 'tumbles', 'cut', 'cuts', 'concern', 'concerns'
]

def get_finance_sentiment(text):
    """
    Enhanced sentiment analysis for finance news
    Combines TextBlob with finance-specific keywords
    """
    text_lower = text.lower()
    
    # Count positive and negative keywords
    positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)
    
    # Use TextBlob for additional context
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
    except:
        polarity = 0
    
    # Combine keyword counting with TextBlob polarity
    if positive_count > negative_count or (positive_count == negative_count and polarity > 0.1):
        return "Positive"
    elif negative_count > positive_count or (positive_count == negative_count and polarity < -0.1):
        return "Negative"
    else:
        return "Neutral"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_finance_news():
    """Fetch and process finance news from RSS feeds"""
    all_articles = []
    
    for source, url in RSS_FEEDS.items():
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
            continue  # Skip failed feeds silently
    
    # Remove duplicates by title
    unique_articles = {}
    for article in all_articles:
        if article['title'] not in unique_articles:
            unique_articles[article['title']] = article
    
    # Process articles and get sentiment
    data = []
    for article in list(unique_articles.values())[:40]:  # Top 40 articles
        sentiment = get_finance_sentiment(article['title'])
        data.append({
            "Title": article['title'],
            "Source": article['source'],
            "Sentiment": sentiment,
            "Link": article['link']
        })
    
    return pd.DataFrame(data)

# ------------------------
# Streamlit UI
# ------------------------
st.title("📈 Finance News Dashboard")
st.markdown("Real-time Indian finance news with intelligent sentiment analysis")
st.divider()

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    sentiment_filter = st.multiselect(
        "Filter by Sentiment",
        ["Positive", "Negative", "Neutral"],
        default=["Positive", "Negative", "Neutral"]
    )
    
    st.divider()
    
    st.markdown("### 📰 News Sources")
    for source in RSS_FEEDS.keys():
        st.markdown(f"• {source}")
    
    st.divider()
    st.info("💡 Click 'Refresh Now' to get latest news")

# Main content
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.metric("Data Source", "Live RSS Feeds")
with col2:
    st.metric("Last Updated", datetime.now().strftime("%I:%M:%S %p"))
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
    st.warning("⚠️ No articles found. Try refreshing again in a moment.")
else:
    # Filter by sentiment
    df_filtered = df[df['Sentiment'].isin(sentiment_filter)]
    
    if df_filtered.empty:
        st.warning("No articles match your sentiment filter. Try selecting more options.")
    else:
        # Display statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total Articles", len(df_filtered))
        with col2:
            positive_count = len(df_filtered[df_filtered['Sentiment'] == 'Positive'])
            st.metric("🟢 Positive", positive_count)
        with col3:
            negative_count = len(df_filtered[df_filtered['Sentiment'] == 'Negative'])
            st.metric("🔴 Negative", negative_count)
        with col4:
            neutral_count = len(df_filtered[df_filtered['Sentiment'] == 'Neutral'])
            st.metric("🟡 Neutral", neutral_count)
        
        st.divider()
        
        # Sentiment distribution chart
        sentiment_counts = df_filtered['Sentiment'].value_counts()
        st.bar_chart(sentiment_counts)
        
        st.divider()
        st.subheader("📰 Latest Headlines")
        
        # Display articles with better styling
        for idx, row in df_filtered.iterrows():
            # Color based on sentiment
            if row['Sentiment'] == 'Positive':
                sentiment_emoji = "🟢"
                border_color = "#28a745"
            elif row['Sentiment'] == 'Negative':
                sentiment_emoji = "🔴"
                border_color = "#dc3545"
            else:
                sentiment_emoji = "🟡"
                border_color = "#ffc107"
            
            st.markdown(
                f"""
                <div style="
                    padding: 20px; 
                    border-left: 5px solid {border_color}; 
                    background-color: #f8f9fa; 
                    border-radius: 5px; 
                    margin-bottom: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h4 style="margin: 0 0 10px 0; color: #212529;">
                        {sentiment_emoji} {row['Title']}
                    </h4>
                    <p style="color: #6c757d; font-size: 14px; margin: 10px 0;">
                        <b>Source:</b> {row['Source']} | <b>Sentiment:</b> {row['Sentiment']}
                    </p>
                    <a href="{row['Link']}" target="_blank" style="text-decoration: none;">
                        <button style="
                            background-color: {border_color}; 
                            color: white; 
                            padding: 10px 20px; 
                            border: none; 
                            border-radius: 5px; 
                            cursor: pointer;
                            font-weight: bold;
                        ">
                            Read Full Article →
                        </button>
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

# Footer
st.divider()
st.caption("Data refreshes automatically. Click 'Refresh Now' for immediate updates.")
