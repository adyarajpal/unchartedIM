import streamlit as st
import requests
import openai
import base64
import weasyprint
import markdown2
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

# ----- DARK THEME & STYLING -----
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
       \n This tool generates a comprehensive <strong>Investment Memorandum</strong> for any given company.
        Simply enter the Company Name and any additional details you'd like to provide, then click <strong>Generate</strong>.
    </div>
""", unsafe_allow_html=True)


# ----- USER INPUT FIELDS -----
company_name = st.text_input("Company Name", "")
details = st.text_area("Details", "")

# ----- GPT PROMPT CONSTRUCTION & CALL -----
def create_investment_memorandum_prompt(company_name, user_details):
    style_guide = (
        "Be concise. Use a professional tone. "
        "Use contemporary and modern sentence structures, phrases and words. "
        "Demonstrate domain expertise. Create content easy to consume for a variety of audience expertise levels. "
        "Stay direct and confident. Do not use adverbs."
    )

    base_outline = f"""
You are a domain expert tasked with writing an investment memorandum for '{company_name}'.
User Details: {user_details}

Follow these guidelines:
- {style_guide}
- Return the entire answer in Markdown format.

Please structure the content using the following outline:

1. Executive Summary
   - Opportunity Overview: ...
   - Key Investment Highlights: ...
   - Transaction Summary: ...

2. Company Overview
   - Business Description: ...
   - History & Milestones: ...
   - Management Team: ...
   - Ownership Structure: ...

3. Market Opportunity
   - Industry Overview: ...
   - Competitive Landscape: ...
   - Addressable Market: ...

4. Business Model & Revenue Drivers
   - Products/Services: ...
   - Customer Segments: ...
   - Pricing Strategy: ...
   - Sales & Marketing Strategy: ...

5. Financial Performance & Projections
   - Historical Financials: ...
   - Key Performance Indicators (KPIs): ...
   - Financial Projections: ...
   - Break-even Analysis: ...

6. Investment Thesis & Rationale
   - Why Now? ...
   - Scalability Potential: ...
   - Exit Strategy: ...

7. Risk Factors & Mitigation
   - Market Risks: ...
   - Operational Risks: ...
   - Financial Risks: ...
   - Mitigation Strategies: ...

8. Transaction Structure & Terms
   - Use of Funds: ...
   - Valuation & Deal Structure: ...
   - Investor Return Scenarios: ...

9. Appendices
   - Detailed Financials: ...
   - Legal & Compliance: ...
   - Supplementary Market Data: ...

Return a cohesive, final investment memorandum in one response, entirely in Markdown.
"""
    return base_outline

def ask_gpt4(prompt_text):
    try:
        response = openai.ChatCompletion.create(
            model="chatgpt-4o-latest",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are a seasoned financial analyst and domain expert. "
                        "Write a thorough investment memorandum following the user's outline and style instructions."
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
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

if st.button("Generate"):
    if not company_name.strip():
        st.warning("Please provide the Company Name")
    else:
        # 1. Build prompt & get GPT output in Markdown
        prompt = create_investment_memorandum_prompt(company_name, details)
        gpt_markdown = ask_gpt4(prompt)

        # 2. Display in Streamlit (optional)
        st.markdown(gpt_markdown)

        # 3. Convert Markdown to HTML
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

        # 4. Convert HTML -> PDF (WeasyPrint)
        pdf_data = weasyprint.HTML(string=full_html).write_pdf()

        # 5. Provide download button for the PDF
        st.download_button(
            label="Download PDF",
            data=pdf_data,
            file_name="investment_memorandum.pdf",
            mime="application/pdf"
        )
