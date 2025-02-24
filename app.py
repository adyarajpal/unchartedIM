import io
import streamlit as st
import openai
import pandas as pd
from xhtml2pdf import pisa

st.title("Parsed GPT Table to PDF")

if st.button("Generate Table"):
    # System prompt for a simple Markdown table
    system_prompt = (
        "You are ChatGPT. Generate a Markdown table with random data. "
        "Output only the table, no triple backticks, no commentary."
    )

    # Get GPT's table
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_prompt}],
        temperature=0.7,
        max_tokens=500
    )
    table_markdown = response["choices"][0]["message"]["content"].strip()

    # Show raw markdown in the app
    st.markdown(table_markdown)

    # Parse GPT’s table lines
    lines = table_markdown.split("\n")

    # First line is the header
    header_line = lines[0]
    # Remainder after the separator
    data_lines = lines[2:]

    # Extract header columns
    headers = [col.strip() for col in header_line.split("|") if col.strip()]

    # Build rows for DataFrame
    rows = []
    for line in data_lines:
        line = line.strip()
        if not line or line.startswith("|-"):
            # Skip empty lines or the separator row
            continue
        # Split row by "|"
        columns = [col.strip() for col in line.split("|") if col.strip()]
        rows.append(columns)

    # Create DataFrame
    df = pd.DataFrame(rows, columns=headers)

    # Convert DataFrame to HTML
    df_html = df.to_html(index=False, border=0)

    # Basic styling
    styled_html = f"""
    <html>
      <head>
        <style>
          body {{
            font-family: Arial, sans-serif;
            margin: 20px;
          }}
          table {{
            border-collapse: collapse;
            width: 80%;
            margin: auto;
          }}
          th, td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
          }}
          th {{
            background-color: #f2f2f2;
          }}
        </style>
      </head>
      <body>
        {df_html}
      </body>
    </html>
    """

    # Use xhtml2pdf to convert HTML to PDF
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(styled_html), dest=pdf_buffer)
    pdf_data = pdf_buffer.getvalue()

    # Download button
    st.download_button(
        label="Download PDF",
        data=pdf_data,
        file_name="parsed_table.pdf",
        mime="application/pdf"
    )
