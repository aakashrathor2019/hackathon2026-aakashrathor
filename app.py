import streamlit as st
import asyncio, pandas as pd, time
from core.agent import process_all_tickets
from core.logger import get_audit_summary
import plotly.express as px

st.set_page_config(page_title='ShopWave AI Ops', layout='wide', page_icon='🛒')
st.title('ShopWave Autonomous Support Agent')
st.caption('Production-ready AI support operations system')

# Sidebar with metrics
st.sidebar.header('System Metrics')
summary = get_audit_summary()
st.sidebar.metric('Total Processed', summary['total_processed'])
st.sidebar.metric('Avg Confidence', f"{summary['avg_confidence']:.2f}")

if summary['recent_actions']:
    st.sidebar.subheader('Recent Actions')
    for action, count in summary['recent_actions'].items():
        st.sidebar.metric(action.title(), count)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    if st.button('Run Ticket Processing', type='primary'):
        with st.spinner('Processing tickets...'):
            start_time = time.time()
            results = asyncio.run(process_all_tickets())
            processing_time = time.time() - start_time

        st.success(f'Processed {len(results)} tickets in {processing_time:.2f}s')

        # Results table
        df = pd.DataFrame(results)
        st.subheader('Processing Results')
        st.dataframe(df, width='stretch', height=400)

        # Key metrics
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric('Tickets Processed', len(df))
        with col_b:
            auto_resolved = len(df[df.action != 'escalate'])
            st.metric('Auto Resolved', auto_resolved)
        with col_c:
            escalated = len(df[df.action == 'escalate'])
            st.metric('Escalated', escalated)

with col2:
    st.subheader('Action Distribution')
    if 'df' in locals() and not df.empty:
        action_counts = df['action'].value_counts()
        fig = px.pie(values=action_counts.values, names=action_counts.index, title='Actions Taken')
        st.plotly_chart(fig, width='stretch')

    st.subheader('Confidence Levels')
    if 'df' in locals() and not df.empty:
        fig2 = px.histogram(df, x='confidence', nbins=10, title='Confidence Distribution')
        st.plotly_chart(fig2, width='stretch')

# Detailed view
if 'results' in locals():
    st.subheader('Detailed Ticket Analysis')
    for result in results[:5]:  # Show first 5
        with st.expander(f"Ticket {result['ticket_id']} - {result['action'].title()}"):
            st.write(f"**Customer:** {result['customer']}")
            st.write(f"**Action:** {result['action']}")
            st.write(f"**Confidence:** {result['confidence']}")
            st.write(f"**Reason:** {result['reason']}")
            if 'factors' in result:
                st.write(f"**Decision Factors:** {', '.join(result['factors'])}")
            st.write(f"**Processing Time:** {result['latency_ms']}ms")

st.markdown('---')
st.caption('Built with ❤️ for ShopWave Hackathon 2026 ~ Aakash Rathor')