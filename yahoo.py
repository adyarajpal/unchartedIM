import streamlit as st
import requests
import openai
import base64
import weasyprint
import markdown2
import yfinance as yf
import time  # <-- For measuring timing

## put in peer companies 
# Optional: Set page config
st.set_page_config(
    page_title="Investment Memorandum Generator",
    layout="centered",
    initial_sidebar_state="auto"
)

# ----- FUNCTION TO CONVERT LOCAL IMAGE TO BASE64 -----
def load_image_as_base64(image_path: str) -> str:
    """Encodes the local image as a base64 string."""
    with open(image_path, "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode()
    return encoded_string

st.markdown(
    """
    <style>
    /* Override the default Streamlit theme */
    body {
        background-color: #1e1e1e;
        color: #f8f8f2;
    }
    .stTextInput > label, .stTextArea > label {
        font-weight: bold;
        color: #f8f8f2;
    }
    .stButton button {
        background-color: #682bd7;
        color: #ffffff;
        border-radius: 0.5rem;
        border: none;
        padding: 0.6rem 1rem;
        font-weight: bold;
        cursor: pointer;
    }
    .stButton button:hover {
        background-color: #7c3ff8;
    }
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 1rem;
        flex-wrap: nowrap;
    }
    .logo-container img {
        width: 60px;
        height: auto;
    }
    </style>
    """,
    unsafe_allow_html=True
)

logo_base64 = load_image_as_base64("uncharted_logo.png")

st.markdown(f"""
<div class="logo-container">
    <img src="data:image/png;base64,{logo_base64}" alt="Company Logo"/>
    <h1 style="margin:0;padding:0;">Investment Memorandum</h1>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-top: 30px;">
   This tool generates a comprehensive <strong>Investment Memorandum</strong> for any given company.
   Provide the Company Name, Ticker Symbol, and any additional details, then click <strong>Generate</strong>.
</div>
""", unsafe_allow_html=True)

company_name = st.text_input("Company Name (e.g. Apple Inc.)", "")
ticker_symbol = st.text_input("Ticker Symbol (e.g. AAPL, TSLA)", "")
details = st.text_area("Additional Details", "")

# Relevant keys for our memo
RELEVANT_KEYS = [
    "longBusinessSummary", "marketCap", "enterpriseValue", "trailingPE",
    "forwardPE", "priceToSalesTrailing12Months", "profitMargins", "operatingMargins",
    "grossMargins", "earningsGrowth", "revenueGrowth", "beta",
    "sharesOutstanding", "floatShares", "heldPercentInsiders", "heldPercentInstitutions",
    "totalRevenue", "ebitda", "freeCashflow", "operatingCashflow", "netIncomeToCommon",
    "dividendRate", "dividendYield", "payoutRatio", "recommendationMean",
    "recommendationKey", "numberOfAnalystOpinions", "currentRatio",
    "quickRatio", "debtToEquity", "address1", "city", "state", "zip",
    "country", "phone", "website", "companyOfficers", "industry", "sector"
]

def fetch_yfinance_data(ticker_symbol):
    """Fetch key financial info via yfinance and return a dict with relevant data."""
    start_time = time.time()
    ticker_data = yf.Ticker(ticker_symbol)
    raw_info = ticker_data.info
    # Extract only the fields we care about
    memo_data = { key: raw_info.get(key, None) for key in RELEVANT_KEYS }
    # End time for data fetch
    elapsed = time.time() - start_time
    print(f"[INFO] Data fetch from yfinance took {elapsed:.2f} seconds.")
    return memo_data

def create_investment_memorandum_prompt(company_name, user_details, financial_data, ticker_symbol):
    style_guide = (
        "Be concise. Use a professional tone. "
        "Use contemporary and modern sentence structures, phrases and words. "
        "Demonstrate domain expertise. Create content easy to consume for a variety of audience expertise levels. "
        "Stay direct and confident. Do not use adverbs."
    )

    # Convert the financial_data dict into a bullet-list or short summary for GPT
    finance_bullets = []
    for k, v in financial_data.items():
        finance_bullets.append(f"- **{k}**: {v}")

    finance_summary = "\n".join(finance_bullets)

    base_outline = f"""
You are a domain expert tasked with writing an investment memorandum for '{company_name}'.
User Details: {user_details}

Below is factual financial data for {company_name}, identified by ticker symbol '{ticker_symbol}':

{finance_summary}

Follow these guidelines:
- {style_guide}
- Incorporate all provided financial data into the appropriate sections of the investment memorandum.
- Return the entire answer in Markdown format.

Please structure the content using the following outline:

1. Executive Summary
   - Opportunity Overview
   - Key Investment Highlights
   - Transaction Summary

2. Company Overview
   - Business Description
   - History & Milestones
   - Management Team
   - Ownership Structure

3. Market Opportunity
   - Industry Overview
   - Competitive Landscape
   - Addressable Market

4. Business Model & Revenue Drivers
   - Products/Services
   - Customer Segments
   - Pricing Strategy
   - Sales & Marketing Strategy

5. Financial Performance & Projections
   - Historical Financials
   - Key Performance Indicators (KPIs)
   - Financial Projections
   - Break-even Analysis

6. Investment Thesis & Rationale
   - Why Now?
   - Scalability Potential
   - Exit Strategy

7. Risk Factors & Mitigation
   - Market Risks
   - Operational Risks
   - Financial Risks
   - Mitigation Strategies

8. Transaction Structure & Terms
   - Use of Funds
   - Valuation & Deal Structure
   - Investor Return Scenarios

9. Appendices
   - Detailed Financials
   - Legal & Compliance
   - Supplementary Market Data

Return a cohesive, final investment memorandum in one response, entirely in Markdown.
"""
    return base_outline

def ask_gpt4(prompt_text):
    start_time = time.time()
    try:
        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a seasoned financial analyst and domain expert. "
                        "Write a thorough investment memorandum following the user's outline, style instructions, "
                        "and the provided financial data."
                    )
                },
                {
                    "role": "user",
                    "content": prompt_text
                }
            ],
            temperature=0.7,
            max_tokens=6000
        )
        gpt_content = response["choices"][0]["message"]["content"]
    except Exception as e:
        gpt_content = f"Error: {e}"

    elapsed = time.time() - start_time
    print(f"[INFO] GPT generation took {elapsed:.2f} seconds.")
    return gpt_content

# ----- BUTTON -----
if st.button("Generate"):
    if not company_name.strip():
        st.warning("Please provide the Company Name.")
    elif not ticker_symbol.strip():
        st.warning("Please provide a Ticker Symbol.")
    else:
        # 1. Fetch data from yfinance
        financial_data = fetch_yfinance_data(ticker_symbol)

        # 2. Build the GPT prompt (including the yfinance data)
        prompt = create_investment_memorandum_prompt(company_name, details, financial_data, ticker_symbol)

        # 3. Call GPT
        gpt_markdown = ask_gpt4(prompt)

        # 4. Display in Streamlit
        st.markdown(gpt_markdown)

        # 5. Convert Markdown to HTML
        html_content = markdown2.markdown(gpt_markdown)

        # OPTIONAL: add extra CSS to style PDF
        custom_css = """
        <style>
          body {
            font-family: 'Helvetica', sans-serif;
            margin: 20px;
          }
          h1, h2, h3 {
            color: #682bd7;
          }
        </style>
        """

        full_html = f"<!DOCTYPE html><html><head>{custom_css}</head><body>{html_content}</body></html>"

        # 6. Convert HTML -> PDF (WeasyPrint)
        pdf_data = weasyprint.HTML(string=full_html).write_pdf()

        # 7. Provide download button for the PDF
        st.download_button(
            label="Download PDF",
            data=pdf_data,
            file_name="investment_memorandum.pdf",
            mime="application/pdf"
        )
