import streamlit as st
import openai
import base64
import weasyprint
import markdown2
import yfinance as yf
import time
import requests
import matplotlib.pyplot as plt
from io import BytesIO

MODEL_NAME = "chatgpt-4o-latest"

# Set your API key again if needed
# openai.api_key = "your-api-key-here"  

def load_image_as_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        encoded_string = base64.b64encode(img_file.read()).decode()
    return encoded_string

# Cache the fetch function for 1 hour (3600 seconds)

@st.cache_data(ttl=3600)
def fetch_yfinance_data(ticker_symbol: str) -> dict:
    retries = 3  # Number of retry attempts
    delay = 5    # Starting delay in seconds
    for attempt in range(retries):
        try:
            start_time = time.time()
            ticker_data = yf.Ticker(ticker_symbol)
            raw_info = ticker_data.info  # This is where the request is made
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
            memo_data = {key: raw_info.get(key, None) for key in RELEVANT_KEYS}
            elapsed = time.time() - start_time
            print(f"[INFO] Data fetch from yfinance took {elapsed:.2f} seconds.")
            return memo_data
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                st.warning("Rate limit exceeded. Retrying after a short delay...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                st.error(f"HTTP error: {e}")
                break
    st.error("Failed to fetch data due to rate limiting. Please try again later.")
    return {}

def create_stock_price_chart(ticker_symbol: str, period: str = "1y") -> str:
    # Fetch historical data for the given period
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period)
    if df.empty:
        return "<p>No stock price data available.</p>"
    
    # Plot the closing price over time
    plt.figure(figsize=(8, 4))
    plt.plot(df.index, df['Close'], label="Close Price")
    plt.title(f"{ticker_symbol} Stock Price ({period})")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    
    # Save the plot to a BytesIO buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close()  # Close the figure to free memory
    
    # Encode the image as base64 and return an HTML image tag
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    img_html = f'<img src="data:image/png;base64,{img_base64}" alt="{ticker_symbol} Stock Price Chart" style="max-width:100%;">'
    return img_html


def call_gpt(system_prompt: str, user_prompt: str, tokens=6000) -> str:
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
    elapsed = time.time() - start_time
    print(f"[INFO] GPT generation took {elapsed:.2f} seconds.")
    return response["choices"][0]["message"]["content"]

def markdown_to_html_with_tables(markdown_text: str) -> str:
    cleaned_text = markdown_text.replace("$", "")
    base_html = markdown2.markdown(markdown_text, extras=["tables"])
    
    custom_css = """
    <style>
        @page {
            margin: 1in;
        }
        body {
            font-family: "Times New Roman", serif;
            margin: 0;
            padding: 0;
            font-size: 11.5pt;
            line-height: 1.5;
            color: #000;
        }
        header {
            text-align: center;
            border-bottom: 1px solid #333;
            margin-bottom: 20px;
            padding-bottom: 8px;
        }
        header h1 {
            font-family: "Times New Roman", serif;
            font-size: 20pt;
            margin: 0;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: "Georgia", serif;
            color: #333;
            margin-top: 16pt;
            margin-bottom: 8pt;
            page-break-after: avoid;
        }
        h1 {
            font-size: 18pt;
            border-bottom: 2px solid #333;
            padding-bottom: 4px;
        }
        h2 {
            font-size: 16pt;
            margin-top: 14pt;
            margin-bottom: 6pt;
        }
        p {
            margin: 0 0 12pt 0;
            text-align: justify;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15pt 0;
            font-size: 11.5pt;
        }
        ul, ol {
            margin: 0 0 12pt 20pt;
            padding: 0;
        }
        ul ul, ol ul, ul ol, ol ol {
            margin-left: 14pt;
            margin-bottom: 0;
            margin-top: 0;
            }
        li {
            margin-bottom: 4pt;
        }
        th, td {
            border: 1px solid #666;
            padding: 5px;
            text-align: left;
        }
        th {
            background-color: #eaeaea;
            font-weight: bold;
        }
        .page-break {
            page-break-before: always;
        }
    </style>
    """

    header_html = """
    <header>
        <h1>Investment Memorandum</h1>
    </header>
    """
    
    full_html = f"<!DOCTYPE html><html><head>{custom_css}</head><body>{header_html}{base_html}</body></html>"
    return full_html

import re

VALID_HOLDERS = {
    "Institutional Holders",
    "Inside Holdings",
    "Retail and Others",
    "Shares Outstanding"
}

def parse_ownership_table(table_markdown: str):
    
    lines = table_markdown.strip().split("\n")
    ownership_data = []
    
    # We skip the header row and separator row if they exist
    for line in lines[2:]:
        line = line.strip()
        if not line or line.startswith("|-"):
            continue
        # Each row might look like:
        # "| Insiders | ~0.07% | Executive & Board Holdings |"
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if len(cells) < 2:
            continue
        
        holder = cells[0]
        if holder not in VALID_HOLDERS:
            continue 
        
        ownership_str = cells[1]
        
        # Attempt to parse something like "~8.1%" into 8.1
        match = re.search(r"([\d.]+)", ownership_str)
        if match:
            try:
                ownership_value = float(match.group(1))
                ownership_data.append((holder, ownership_value))
            except ValueError:
                pass
    
    return ownership_data

def create_ownership_pie(ownership_data):
  
    if not ownership_data:
        return "<p>No valid ownership percentage data found.</p>"
    
    labels = [item[0] for item in ownership_data]
    values = [item[1] for item in ownership_data]
    
    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
    plt.title("Ownership Structure")
    
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close()
    
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    img_html = f'<img src="data:image/png;base64,{img_base64}" alt="Ownership Pie Chart" style="max-width:100%;">'
    return img_html


def main():
    st.set_page_config(
        page_title="Multi-Call Memo Generator",
        layout="centered",
        initial_sidebar_state="auto"
    )
    
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

    # User Inputs
    company_name = st.text_input("Company Name (e.g. Apple Inc.)", "")
    ticker_symbol = st.text_input("Ticker Symbol (e.g. AAPL, TSLA)", "")
    details = st.text_area("Additional Details", "")

    if st.button("Generate"):
        if not company_name.strip():
            st.warning("Please provide the Company Name.")
        elif not ticker_symbol.strip():
            st.warning("Please provide a Ticker Symbol.")
        else:
            # 1) Fetch YFinance data (caching in effect)
            financial_data = fetch_yfinance_data(ticker_symbol)
            finance_bullets = [f"- **{k}**: {v}" for k, v in financial_data.items()]
            finance_summary = "\n".join(finance_bullets)

            # Revised System Prompt for GPT calls
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

            all_sections_markdown = []

            # --- Section 1: Executive Summary & Company Overview ---
            user_prompt_1 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 1**: 'Executive Summary & Company Overview' with the following content:
1. Opportunity Overview: Summarize the company's core growth angle, recent strategic moves, and headline financial metrics (revenue, EBITDA, margins).
2. Key Investment Highlights: List at least 4-5 bullet points with strong data references.
3. Transaction Summary: Describe the nature of the transaction or investment round, approximate valuation range, and potential use of proceeds.
4. Business Description: Provide a thorough summary of products/services, revenue sources, and geographic reach. Include references to trailing P/E, forward P/E, and total revenue if available.
5. History & Milestones: Highlight founding date, pivotal expansions, acquisitions, or major product launches.
6. Management Team: Include roles, relevant backgrounds, and any notable credentials.
7. Ownership Structure: Provide a Markdown table with columns: Shareholder, Stake (%), and optionally Notes. Only list these rows exactly: Institutional Holders, Inside Holdings, Retail and Others, and Shares Outstanding.

Emphasize data and detail. Ensure this section alone would fill around 2-3 pages in a typical PDF.
Use tables or bullet points for clarity.
"""
            sec1_markdown = call_gpt(system_style, user_prompt_1)
            sec1_markdown = sec1_markdown.replace("```markdown", "").replace("```", "")
            
            ownership_data = parse_ownership_table(sec1_markdown)
            if ownership_data:
                pie_html = create_ownership_pie(ownership_data)
                sec1_markdown += "\n\n## Ownership Breakdown (Pie Chart)\n\n" + pie_html
            
            all_sections_markdown.append(sec1_markdown)
            

            # --- Section 2: Market Opportunity ---
            user_prompt_2 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 2**: 'Market Opportunity' covering:
1. Industry Overview: Outline total available market size, recent growth rates, and industry trends.
2. Competitive Landscape: Compare the company with 2-3 direct competitors, noting market caps, valuations, or margin profiles.
3. Addressable Market (TAM, SAM, SOM): Break down the broader market, the target segment, and realistic market share.

Provide enough granularity and numeric depth to span 2-3 pages.
Use headings, bullet points, and tables.
"""
            sec2_markdown = call_gpt(system_style, user_prompt_2)
            sec2_markdown = sec2_markdown.replace("```markdown", "").replace("```", "")
            all_sections_markdown.append(sec2_markdown)

            # --- Section 3: Business Model & Revenue Drivers ---
            user_prompt_3 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 3**: 'Business Model & Revenue Drivers' covering:
1. Products/Services: Explain the key offerings, pricing tiers, and unique selling points.
2. Customer Segments: Discuss B2B vs. B2C splits or major client types.
3. Pricing Strategy: Describe how the company sets prices, potential for upselling, and market alignment.
4. Sales & Marketing Strategy: Detail distribution channels, digital marketing, and brand partnerships.

Aim for 2-3 pages of analysis. Use subheadings, bullet points, and tables.
"""
            sec3_markdown = call_gpt(system_style, user_prompt_3)
            sec3_markdown = sec3_markdown.replace("```markdown", "").replace("```", "")
            all_sections_markdown.append(sec3_markdown)

            # --- Section 4: Financial Performance & Projections + Investment Thesis ---
            user_prompt_4 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 4**: 'Financial Performance & Projections + Investment Thesis' with:
1. Historical Financials: Show multi-year revenue trends, net income, EBITDA, and margins (include a table if possible).
2. Key Performance Indicators (KPIs): Highlight 3-4 relevant metrics.
3. Financial Projections (3-5 years): Forecast revenue, EBITDA, and FCF with growth assumptions.
4. Break-even Analysis: Provide numeric examples.
5. Why Now?: Tie in market conditions and company readiness.
6. Scalability Potential and Exit Strategy: Outline growth paths and potential exit scenarios.

Ensure this section fills 2-3 pages. Use bullet points and tables for numeric data.
"""
            sec4_markdown = call_gpt(system_style, user_prompt_4)
            sec4_markdown = sec4_markdown.replace("```markdown", "").replace("```", "")
            stock_chart_html = create_stock_price_chart(ticker_symbol, period="1y")
            sec4_markdown += "\n\n## Stock Price Chart\n\n" + stock_chart_html
            all_sections_markdown.append(sec4_markdown)

            # --- Section 5: Risk Factors, Transaction Terms & Appendices ---
            user_prompt_5 = f"""
Company Name: {company_name}
Ticker: {ticker_symbol}
Additional User Details: {details}

Yahoo Finance Data (raw key-value pairs):
{finance_summary}

Write **Section 5**: 'Risk Factors & Mitigation, Transaction Structure & Terms, Appendices' covering:
1. Risk Factors & Mitigation: Identify at least 5 major risks and recommended mitigation steps.
2. Transaction Structure & Terms: Describe the investment round, valuation, investor rights, and board composition.
3. Appendices: Reference financial statements, legal documents, and market data.
4. Final Concluding Statement: Provide a confident conclusion and call to action.

Ensure this section spans 2-3 pages and uses bullet points, tables, and clear headings.
"""
            sec5_markdown = call_gpt(system_style, user_prompt_5)
            sec5_markdown = sec5_markdown.replace("```markdown", "").replace("```", "")
            all_sections_markdown.append(sec5_markdown)

            # Combine all sections into final_markdown
            final_markdown = (
                "# Investment Memorandum\n\n" +
                "\n\n".join(all_sections_markdown)
            )

            final_markdown = final_markdown.replace("# Investment Memorandum", "")
            st.markdown(final_markdown, unsafe_allow_html = True)

            pdf_html = markdown_to_html_with_tables(final_markdown)
            pdf_data = weasyprint.HTML(string=pdf_html).write_pdf()

            # Provide the Download PDF button
            st.download_button(
                label="Download PDF",
                data=pdf_data,
                file_name="investment_memorandum.pdf",
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
