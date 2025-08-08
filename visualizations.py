import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

def create_kpi_cards(df, region_name):
    """Create KPI cards for the dashboard"""
    if df.empty:
        return None
    
    # Calculate metrics
    total_lipas = len(df)
    lipas_30_days = len(df[df['Day'] > 30])
    lipas_60_days = len(df[df['Day'] > 60])
    
    # Calculate LIPAs closed this month (assuming 'Process status' indicates closure)
    current_month = datetime.now().month
    current_year = datetime.now().year
    this_month = df[df['LIPA Created On'].dt.month == current_month]
    closed_this_month = len(this_month[this_month['Process status'].astype(str).str.contains('closed|completed', case=False, na=False)])
    
    avg_aging_days = df['Day'].mean()
    
    # Create columns for KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🔢 Total Open LIPAs", f"{total_lipas:,}")
    with col2:
        st.metric("🟡 LIPAs > 30 Days", f"{lipas_30_days:,}", 
                 f"{lipas_30_days/total_lipas*100:.1f}%" if total_lipas > 0 else "0%")
    with col3:
        st.metric("🔴 LIPAs > 60 Days", f"{lipas_60_days:,}",
                 f"{lipas_60_days/total_lipas*100:.1f}%" if total_lipas > 0 else "0%")
    with col4:
        st.metric("✅ LIPAs Closed This Month", f"{closed_this_month:,}")
    with col5:
        st.metric("⏱️ Avg. Aging Days", f"{avg_aging_days:.1f}")

def create_aging_trend(df, region_name):
    """Create LIPA Aging Trend line chart"""
    if df.empty:
        return None
    
    # Create weekly bins
    df_weekly = df.copy()
    df_weekly['Week'] = df_weekly['LIPA Created On'].dt.to_period('W').dt.start_time
    
    # Group by week and count LIPAs in different age groups
    weekly_counts = df_weekly.groupby('Week').agg(
        total=('LIPA No. / Delivery', 'count'),
        over_30_days=('Day', lambda x: (x > 30).sum()),
        over_60_days=('Day', lambda x: (x > 60).sum())
    ).reset_index()
    
    # Create line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=weekly_counts['Week'],
        y=weekly_counts['total'],
        name='Total LIPAs',
        line=dict(color='#1f77b4', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=weekly_counts['Week'],
        y=weekly_counts['over_30_days'],
        name='>30 Days',
        line=dict(color='#ff7f0e', width=2, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=weekly_counts['Week'],
        y=weekly_counts['over_60_days'],
        name='>60 Days',
        line=dict(color='#d62728', width=2, dash='dot')
    ))
    
    fig.update_layout(
        title=f"{region_name} - LIPA Aging Trend",
        xaxis_title="Week",
        yaxis_title="Number of LIPAs",
        legend_title="Aging Bucket",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_aging_distribution(df, region_name):
    """Create Aging Bucket Distribution bar chart"""
    if df.empty:
        return None
    
    # Create age buckets
    bins = [0, 30, 60, 90, float('inf')]
    labels = ['0-30 days', '31-60 days', '61-90 days', '>90 days']
    df['Age Bucket'] = pd.cut(df['Day'], bins=bins, labels=labels, right=False)
    
    # Count by age bucket and reason
    age_reason_counts = df.groupby(['Age Bucket', 'Reason code desc.']).size().reset_index(name='Count')
    
    # Create stacked bar chart
    fig = px.bar(
        age_reason_counts, 
        x='Age Bucket', 
        y='Count',
        color='Reason code desc.',
        title=f"{region_name} - Aging Bucket Distribution by Reason",
        labels={'Count': 'Number of LIPAs', 'Reason code desc.': 'Reason Code'},
        category_orders={"Age Bucket": labels}
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_reason_distribution(df, region_name):
    """Create LIPAs by Reason horizontal bar chart"""
    if df.empty:
        return None
    
    # Count by reason
    reason_counts = df['Reason code desc.'].value_counts().reset_index()
    reason_counts.columns = ['Reason', 'Count']
    
    # Create horizontal bar chart
    fig = px.bar(
        reason_counts, 
        x='Count', 
        y='Reason',
        orientation='h',
        title=f"{region_name} - LIPAs by Reason",
        labels={'Count': 'Number of LIPAs', 'Reason': 'Reason Code'},
        color='Count',
        color_continuous_scale='Blues'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_status_donut(df, region_name):
    """Create Process Status donut chart"""
    if df.empty:
        return None
    
    # Count by process status
    status_counts = df['Process status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    
    # Create donut chart
    fig = go.Figure(data=[go.Pie(
        labels=status_counts['Status'],
        values=status_counts['Count'],
        hole=0.5,
        textinfo='label+percent',
        insidetextorientation='radial'
    )])
    
    fig.update_layout(
        title=f"{region_name} - LIPAs by Process Status",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_top_aging_table(df, region_name):
    """Create Top 10 Aging LIPAs table"""
    if df.empty:
        return None
    
    # Get top 10 oldest LIPAs
    top_aging = df.nlargest(10, 'Day')[['LIPA No. / Delivery', 'LIPA Created On', 'Day', 
                                      'Material number', 'Customer Ref. Ord.No.', 'Reason code desc.']]
    
    # Format columns
    top_aging['LIPA Created On'] = top_aging['LIPA Created On'].dt.strftime('%Y-%m-%d')
    
    st.subheader(f"{region_name} - Top 10 Aging LIPAs")
    st.dataframe(
        top_aging,
        column_config={
            'LIPA No. / Delivery': 'LIPA No.',
            'LIPA Created On': 'Created On',
            'Day': 'Days Open',
            'Material number': 'Material',
            'Customer Ref. Ord.No.': 'Customer Ref',
            'Reason code desc.': 'Reason'
        },
        use_container_width=True,
        hide_index=True
    )

def create_heatmap(df, region_name):
    """Create Heat Map: LIPAs by Model vs. Reason"""
    if df.empty:
        return None
    
    # Extract model series (first 3-4 characters of material number)
    df['Model'] = df['Material number'].astype(str).str[:4]
    
    # Create pivot table for heatmap
    heatmap_data = df.pivot_table(
        index='Model',
        columns='Reason code desc.',
        values='LIPA No. / Delivery',
        aggfunc='count',
        fill_value=0
    ).reset_index()
    
    # Create heatmap
    fig = px.imshow(
        heatmap_data.set_index('Model'),
        labels=dict(x="Reason", y="Model", color="Count"),
        title=f"{region_name} - LIPAs by Model vs. Reason",
        color_continuous_scale='YlOrRd'
    )
    
    fig.update_xaxes(side="bottom")
    fig.update_layout(
        xaxis_title="Reason",
        yaxis_title="Model",
        coloraxis_colorbar_title="Count"
    )
    
    st.plotly_chart(fig, use_container_width=True)
