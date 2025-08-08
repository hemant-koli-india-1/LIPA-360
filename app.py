import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Import visualization functions
from visualizations import (
    create_kpi_cards,
    create_aging_trend,
    create_aging_distribution,
    create_reason_distribution,
    create_status_donut,
    create_top_aging_table,
    create_heatmap
)

# Page config
st.set_page_config(
    page_title="LIPA - 360",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {font-size:24px; color: #1f77b4; font-weight: 700;}
    .sub-header {font-size:18px; color: #2c3e50; margin-top: 20px;}
    .success-msg {color: #27ae60; font-weight: 500;}
    .stButton>button {background-color: #3498db; color: white;}
    .stButton>button:hover {background-color: #2980b9;}
    .stDownloadButton>button {background-color: #2ecc71; color: white;}
    .stDownloadButton>button:hover {background-color: #27ae60;}
    .stDataFrame {margin-top: 20px;}
    </style>
""", unsafe_allow_html=True)

def process_data(uploaded_file):
    """Process the uploaded Excel file and return USA and Germany DataFrames"""
    try:
        # Read the Excel file
        df = pd.read_excel(uploaded_file, dtype=str)
        
        # Process the data
        df['LIPA Created On'] = pd.to_datetime(df['LIPA Created On'], errors='coerce')
        df['Today'] = pd.to_datetime(datetime.today().date())
        df['Day'] = (df['Today'] - df['LIPA Created On']).dt.days
        
        def clean_lipa(row):
            if pd.notna(row.get('Combined Status')) and "GSS Classic" in str(row['Combined Status']):
                return "GSS classic"
            return str(row.get('LIPA EX33 FZ / ExtDlvID')) if pd.notna(row.get('LIPA EX33 FZ / ExtDlvID')) else None
        
        df['LIPA EX33 FZ / ExtDlvID'] = df.apply(clean_lipa, axis=1)
        df['Region'] = df['LIPA EX33 FZ / ExtDlvID'].astype(str).str.startswith('7').map({True: 'USA', False: 'Germany'})
        df['Reason code desc.'] = df['Reason code desc.'].fillna("").replace("", "GSS classic")
        df.loc[df['Reason code desc.'] == 'GSS classic', 'LIPA EX33 FZ / ExtDlvID'] = ""
        df = df[df['Day'] > 10]
        
        required_cols = [
            'LIPA EX33 FZ / ExtDlvID', 'LIPA Created On', 'Day',
            'LIPA No. / Delivery', 'Process status', 'Reason code desc.',
            'Customer Ref. Ord.No.', 'Material number', 'Material Description',
            'Delivery Quantity', 'Model series'
        ]
        
        def prepare_df(region_df):
            region_df = region_df[required_cols].copy()
            region_df = region_df.sort_values(by='Day', ascending=False).reset_index(drop=True)
            region_df.insert(0, 'Sr No.', range(1, len(region_df) + 1))
            return region_df
        
        usa_df = prepare_df(df[df['Region'] == 'USA']) if 'USA' in df['Region'].values else pd.DataFrame()
        germany_df = prepare_df(df[df['Region'] == 'Germany']) if 'Germany' in df['Region'].values else pd.DataFrame()
        
        return True, usa_df, germany_df
    except Exception as e:
        return False, str(e), None

def get_table_download_link(df, filename, button_text):
    """Generates a link to download the dataframe as an Excel file"""
    if df.empty:
        return ""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    b64 = base64.b64encode(output.getvalue()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">\
            <button class="stDownloadButton">{button_text}</button></a>'
    return href

def send_email(receiver_email, subject, body, attachment=None, filename=None):
    """Send email with optional attachment"""
    try:
        # Email configuration - replace with your SMTP settings
        sender_email = st.secrets.get("email", "your-email@example.com")
        password = st.secrets.get("password", "your-password")
        smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets.get("smtp_port", 587)
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach file if provided
        if attachment is not None and filename:
            part = MIMEApplication(attachment, Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)

# App Header
st.title("📊 LIPA - 360")
st.markdown("<div class='sub-header'>Process and analyze LIPA data with ease</div>", unsafe_allow_html=True)

# File Upload
st.sidebar.header("1. Upload Excel File")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Process the file
    with st.spinner('Processing your file...'):
        success, usa_df, germany_df = process_data(uploaded_file)
    
    if success:
        st.sidebar.success("File processed successfully!")
        
        # Display USA Data
        if not usa_df.empty:
            st.header("📊 USA Data Analysis")
            
            # 1. KPI Cards
            st.subheader("Key Metrics")
            create_kpi_cards(usa_df, "USA")
            
            # 2. Aging Trend
            st.subheader("Aging Trend")
            create_aging_trend(usa_df, "USA")
            
            # 3. Aging Distribution
            st.subheader("Aging Bucket Distribution")
            create_aging_distribution(usa_df, "USA")
            
            # 4. Reason Distribution
            st.subheader("LIPAs by Reason")
            create_reason_distribution(usa_df, "USA")
            
            # 5. Process Status
            st.subheader("Process Status Distribution")
            create_status_donut(usa_df, "USA")
            
            # 6. Top Aging Table
            create_top_aging_table(usa_df, "USA")
            
            # 7. Heatmap
            st.subheader("LIPAs by Model vs. Reason")
            create_heatmap(usa_df, "USA")
            
            # Raw Data Section
            with st.expander("View Raw USA Data"):
                st.dataframe(usa_df, use_container_width=True)
                st.markdown(get_table_download_link(
                    usa_df, 
                    "USA_NotDispatched.xlsx", 
                    "⬇️ Download USA Data"
                ), unsafe_allow_html=True)
        else:
            st.warning("No USA data found in the uploaded file.")
        
        # Add a divider between regions
        st.markdown("---")
        
        # Display Germany Data
        if not germany_df.empty:
            st.header("📊 Germany Data Analysis")
            
            # 1. KPI Cards
            st.subheader("Key Metrics")
            create_kpi_cards(germany_df, "Germany")
            
            # 2. Aging Trend
            st.subheader("Aging Trend")
            create_aging_trend(germany_df, "Germany")
            
            # 3. Aging Distribution
            st.subheader("Aging Bucket Distribution")
            create_aging_distribution(germany_df, "Germany")
            
            # 4. Reason Distribution
            st.subheader("LIPAs by Reason")
            create_reason_distribution(germany_df, "Germany")
            
            # 5. Process Status
            st.subheader("Process Status Distribution")
            create_status_donut(germany_df, "Germany")
            
            # 6. Top Aging Table
            create_top_aging_table(germany_df, "Germany")
            
            # 7. Heatmap
            st.subheader("LIPAs by Model vs. Reason")
            create_heatmap(germany_df, "Germany")
            
            # Raw Data Section
            with st.expander("View Raw Germany Data"):
                st.dataframe(germany_df, use_container_width=True)
                st.markdown(get_table_download_link(
                    germany_df, 
                    "Germany_NotDispatched.xlsx", 
                    "⬇️ Download Germany Data"
                ), unsafe_allow_html=True)
        else:
            st.warning("No Germany data found in the uploaded file.")
        
        # Email Section
        st.sidebar.header("2. Email Options")
        email = st.sidebar.text_input("Enter recipient email")
        email_subject = st.sidebar.text_input("Email Subject", "LIPA Data Report")
        email_body = st.sidebar.text_area("Email Body", "Please find attached the LIPA data report.")
        
        if st.sidebar.button("📧 Send Email"):
            if email:
                # Create a single Excel file with both sheets for email
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if not usa_df.empty:
                        usa_df.to_excel(writer, sheet_name='USA', index=False)
                    if not germany_df.empty:
                        germany_df.to_excel(writer, sheet_name='Germany', index=False)
                
                # Send email with attachment
                success, message = send_email(
                    email,
                    email_subject,
                    email_body,
                    attachment=output.getvalue(),
                    filename="LIPA_NotDispatched_Report.xlsx"
                )
                
                if success:
                    st.sidebar.success("Email sent successfully!")
                else:
                    st.sidebar.error(f"Failed to send email: {message}")
            else:
                st.sidebar.warning("Please enter a recipient email address.")
    else:
        st.error(f"Error processing file: {usa_df}")
else:
    st.info("👈 Please upload an Excel file to get started.")
    
    # Instructions
    with st.expander("ℹ️ How to use this app"):
        st.markdown("""
        1. Click on "Browse files" or drag and drop your Excel file
        2. The app will process the data and display USA and Germany data separately
        3. Use the download buttons to save the processed data
        4. Optionally, send the report via email using the sidebar form
        
        **Note:** The app filters records older than 10 days.
        """)
