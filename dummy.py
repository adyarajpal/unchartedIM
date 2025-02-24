import streamlit as st
import openai
import base64
import weasyprint
import markdown2
import yfinance as yf
import time

MODEL_NAME = "chatgpt-4o-latest"

st.set_page_config(
    page_title="Multi-Call Memo Generator",
    layout="centered",
    initial_sidebar_state="auto"
)

# ---------------------------
# Encode local image to base64
# ---------------------------
def load_image_as_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode()
    return encoded_string

# ---------------------------
# Basic custom styling
# ---------------------------
st.markdown(
    """
    <style>
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

# ---------------------------
# Display logo/header
# ---------------------------
logo_base64 = load_image_as_base64("uncharted_logo.png")
st.markdown(f"""
<div class="logo-container">
    <img src="data:image/png;base64,{logo_base64}" alt="Company Logo"/>
    <h1 style="margin:0;padding:0;">Investment Memorandum (Multi-Call)</h1>
</div>
""", unsafe_allow_html=True)

st.markdown(
    """
    <div style="margin-top: 30px;">
       This tool generates each section of an <strong>Investment Memorandum</strong> in separate GPT calls, 
       creating short bullet summaries between sections to avoid repeated content.
       Provide the Company Name, Ticker Symbol, and any details, then click <strong>Generate</strong>.
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# User Inputs
# ---------------------------
company_name = st.text_input("Company Name (e.g. Apple Inc.)", "")
ticker_symbol = st.text_input("Ticker Symbol (e.g. AAPL, TSLA)", "")
details = st.text_area("Additional Details", "")

# ---------------------------
# YFinance data keys
# ---------------------------
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

def fetch_yfinance_data(ticker_symbol: str) -> dict:
    """Fetch key financial info via yfinance."""
    start_time = time.time()
    ticker_data = yf.Ticker(ticker_symbol)
    raw_info = ticker_data.info
    memo_data = {key: raw_info.get(key, None) for key in RELEVANT_KEYS}
    elapsed = time.time() - start_time
    print(f"[INFO] Data fetch from yfinance took {elapsed:.2f} seconds.")
    return memo_data

# ---------------------------
# GPT helpers
# ---------------------------
def call_gpt(system_prompt: str, user_prompt: str, tokens=6000) -> str:
    """Calls OpenAI ChatCompletion, returns content, logs timing."""
    start_time = time.time()
    response = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=tokens
    )
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"[INFO] GPT generation took {elapsed:.2f} seconds.")
    return response["choices"][0]["message"]["content"]

# ---------------------------
# Main logic
# ---------------------------
if st.button("Generate"):
    if not company_name.strip():
        st.warning("Please provide the Company Name.")
    elif not ticker_symbol.strip():
        st.warning("Please provide a Ticker Symbol.")
    else:
        # 1) fetch YFinance data
        financial_data = fetch_yfinance_data(ticker_symbol)
        finance_bullets = [f"- **{k}**: {v}" for k, v in financial_data.items()]
        finance_summary = "\n".join(finance_bullets)

        # ---------------------------------------------
        # Revised System Prompt for each GPT call
        # ---------------------------------------------
        system_style = (
            "You are a seasoned financial analyst at a major investment bank. "
            "Produce one section of an Investment Memorandum that is data-driven, thorough, "
            "and spans at least 2-3 pages in typical PDF format. "
            "Integrate available numeric data from the Yahoo Finance details. "
            "Write in an engaging yet confident tone. "
            "Use modern phrasing, domain expertise, and a touch of humor. "
            "Avoid adverbs. "
            "Use headings, bullet points, tables, and bold formatting for clarity. "
            "Return only the requested section in valid Markdown."
        )

        # We'll store each section's text
        all_sections_markdown = []

        # ======================
        # Section 1: Exec Summ & Company Overview
        # ======================
        user_prompt_1 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 1**: 'Executive Summary & Company Overview' with the following content:
1. Opportunity Overview: Summarize the company's core growth angle, recent strategic moves, and headline financial metrics (revenue, EBITDA, margins).
2. Key Investment Highlights: List at least 4-5 bullet points with strong data references (e.g., YoY revenue growth, relevant ratios, market share).
3. Transaction Summary: Describe the nature of the transaction or investment round, approximate valuation range, and potential use of proceeds.
4. Business Description: Provide a thorough summary of products/services, revenue sources, and geographic reach. Include references to trailing P/E, forward P/E, and total revenue if available.
5. History & Milestones: Highlight founding date, pivotal expansions, acquisitions, or major product launches.
6. Management Team: Include roles, relevant backgrounds, and any notable credentials.
7. Ownership Structure: Cite insider holdings, major institutional stakes, and shares outstanding.

Emphasize data and detail. Ensure this section alone would fill around 2-3 pages in a typical PDF. 
Use tables or bullet points for clarity. Provide numeric insights from the Yahoo Finance data. 
Avoid repeating content from other sections.
"""
        sec1_markdown = call_gpt(system_style, user_prompt_1)
        sec1_markdown = sec1_markdown.replace("```markdown", "").replace("```", "")

        all_sections_markdown.append(sec1_markdown)

        # ======================
        # Section 2: Market Opportunity
        # ======================
        user_prompt_2 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 2**: 'Market Opportunity' covering:
1. Industry Overview: Outline total available market size, recent growth rates, and industry trends. Reference at least one numeric indicator, such as average revenue growth across the sector or relevant ratio from the data.
2. Competitive Landscape: Compare the company with at least 2-3 direct competitors. Note their market caps, valuations, or margin profiles. Include a brief table if possible.
3. Addressable Market (TAM, SAM, SOM): Provide a breakdown of the broader market, the segment the company targets, and the share it might realistically capture. Incorporate references to relevant market data or key growth drivers.

Provide enough granularity and numeric depth to span 2-3 pages in a typical PDF. 
Use headings, bullet points, and short tables. Integrate numbers from Yahoo Finance data if relevant.
"""
        sec2_markdown = call_gpt(system_style, user_prompt_2)
        sec2_markdown = sec2_markdown.replace("```markdown", "").replace("```", "")

        all_sections_markdown.append(sec2_markdown)

        # ======================
        # Section 3: Business Model & Revenue Drivers
        # ======================
        user_prompt_3 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 3**: 'Business Model & Revenue Drivers' covering:
1. Products/Services: Explain the key offerings, pricing tiers, and unique selling points. Highlight gross margins if relevant.
2. Customer Segments: Discuss B2B vs. B2C splits or major client types. Include references to revenue distribution by geography or segment if data is available.
3. Pricing Strategy: Showcase how the company sets prices, potential for upselling or cross-selling, and alignment with market trends.
4. Sales & Marketing Strategy: Detail distribution channels, digital marketing, and brand partnerships. Reference any relevant operating margins or marketing spend (if available).

Aim for 2-3 pages of dense analysis. Integrate numeric data where possible (margins, revenue breakdown, etc.). 
Present the information in clear subheadings, bullet points, and tables.
"""
        sec3_markdown = call_gpt(system_style, user_prompt_3)
        sec3_markdown = sec3_markdown.replace("```markdown", "").replace("```", "")

        all_sections_markdown.append(sec3_markdown)

        # ======================
        # Section 4: Financial Performance & Projections + Investment Thesis
        # ======================
        user_prompt_4 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 4**: 'Financial Performance & Projections + Investment Thesis' with:
1. Historical Financials: Show multi-year revenue trends, net income, EBITDA, and margins. Provide a table if possible (at least 3 years). Cite growth rates or changes in margins.
2. Key Performance Indicators (KPIs): Highlight at least 3-4 metrics (e.g., ARPU, churn, customer acquisition cost) if relevant.
3. Financial Projections (3-5 years): Include revenue, EBITDA, and FCF forecasts. Show projected growth rates, margin expansion, or major assumptions.
4. Break-even Analysis: Indicate operational or cash-flow break-even thresholds with numeric examples.
5. Why Now?: Tie in current market conditions, the company's readiness, and macroeconomic indicators. Reference any relevant Yahoo Finance data (beta, share price trends, etc.).
6. Scalability Potential: Outline paths for expansion or product line growth.
7. Exit Strategy: Discuss possible IPO, acquisition, or secondary sale. Mention potential valuations or multiples.

Produce enough detail to fill 2-3 pages. Present numeric info in bullet points or tables.
"""
        sec4_markdown = call_gpt(system_style, user_prompt_4)
        sec4_markdown = sec4_markdown.replace("```markdown", "").replace("```", "")

        all_sections_markdown.append(sec4_markdown)

        # ======================
        # Section 5: Risk Factors, Transaction Terms & Appendices
        # ======================
        user_prompt_5 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 5**: 'Risk Factors & Mitigation, Transaction Structure & Terms, Appendices' covering:
1. Risk Factors & Mitigation: Identify at least 5 major risks (market, product, regulatory, competition, financing). Offer numeric context where possible (e.g., debt-to-equity, quick ratio). Present recommended mitigation steps.
2. Transaction Structure & Terms: Describe the investment round size, equity or convertible notes, valuation approach, potential investor rights, and board composition. Include references to ownership percentages or insider stakes if relevant.
3. Appendices: Include references to financial statements (income statement, balance sheet, cash flow), legal/regulatory documents, and supplementary market data. Summarize additional exhibits.
4. Final Concluding Statement: Provide a confident conclusion and call to action.

Write enough text to span 2-3 pages. Cite specific numeric data (ratios, ownership levels, etc.) and structure the content in headings, subheadings, bullet points, and tables.
"""
        sec5_markdown = call_gpt(system_style, user_prompt_5)
        sec5_markdown = sec5_markdown.replace("```markdown", "").replace("```", "")

        all_sections_markdown.append(sec5_markdown)

        # ---------------------------
        # Combine all sections
        # ---------------------------
        final_markdown = (
            "# Investment Memorandum\n\n"
            f"{sec1_markdown}\n\n"
            f"{sec2_markdown}\n\n"
            f"{sec3_markdown}\n\n"
            f"{sec4_markdown}\n\n"
            f"{sec5_markdown}\n"
        )

        # Show final output in Streamlit
        st.markdown(final_markdown)

        # Convert to HTML for PDF
        html_content = markdown2.markdown(final_markdown)
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
        pdf_data = weasyprint.HTML(string=full_html).write_pdf()

        st.download_button(
            label="Download PDF",
            data=pdf_data,
            file_name="investment_memorandum.pdf",
            mime="application/pdf"
        )
