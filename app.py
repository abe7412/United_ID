import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import re
import tempfile
import os

st.set_page_config(page_title="Muqeem Form Filler", layout="centered")

st.title("📝 Muqeem PDF Form Filler")
st.markdown("Upload a **Muqeem PDF** and a **form PDF** with fillable fields.")

# ---------- Upload PDFs ----------
muqeem_file = st.file_uploader("📄 Upload Muqeem PDF", type="pdf")
form_file = st.file_uploader("📋 Upload Form PDF (fillable)", type="pdf")

# ---------- Helper: Extract Muqeem Data ----------
def extract_muqeem_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

    data = {}

    name_match = re.search(r"Name\s+(.*?)\s+Translated Name", text)
    data["Name"] = name_match.group(1).strip() if name_match else "Not found"

    nationality_match = re.search(r"Nationality\s+([^\n]+)", text)
    data["Nationality"] = nationality_match.group(1).strip() if nationality_match else None

    passport_match = re.search(r"Passport Information\s+Number\s+([A-Z0-9]+)", text, re.IGNORECASE)
    data["Passport"] = passport_match.group(1).strip() if passport_match else "Not found"

    issue_date_match = re.search(r"Issue Date\s+([0-9\-]+)\s+Expiry Date", text)
    data["IssueDate"] = issue_date_match.group(1).strip() if issue_date_match else "Not found"

    issue_loc_match = re.search(r"Issue Location\s+(.+?)\s+Iqama Information", text)
    data["IssueLocation"] = issue_loc_match.group(1).strip() if issue_loc_match else "Not found"

    birth_date_match = re.search(r"Birth Date\s+([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    data["BirthDate"] = birth_date_match.group(1) if birth_date_match else "Not found"

    iqama_match = re.search(r"Iqama Number\s+(\d+)", text)
    data["Iqama"] = iqama_match.group(1).strip() if iqama_match else None

    data["BloodType"] = "B+"
    return data

# ---------- Main Process ----------
if muqeem_file and form_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as muqeem_temp:
        muqeem_temp.write(muqeem_file.read())
        muqeem_pdf_path = muqeem_temp.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as form_temp:
        form_temp.write(form_file.read())
        form_pdf_path = form_temp.name

    data = extract_muqeem_data(muqeem_pdf_path)

    # Validate required fields
    if not data.get("Name") or not data.get("Iqama"):
        st.error("❌ Required fields missing from Muqeem data.")
    else:
        start_day, start_month, start_year = "11", "11", "1111"
        end_day, end_month, end_year = "11", "11", "1111"
        po = "48992"

        fields_to_fill = {
            "fill_5": data["Name"],
            "fill_6": data["Nationality"],
            "fill_7": data["Iqama"],
            "fill_8": data["Passport"],
            "fill_9": f"{data['IssueDate']} - {data['IssueLocation']}",
            "fill_10": data["BirthDate"],
            "fill_11": data["BloodType"],
            "Text2": start_day,
            "Text3": start_month,
            "Text4": start_year,
            "Text5": end_day,
            "Text6": end_month,
            "Text7": end_year,
            "Text1": po
        }

        # Fill PDF
        doc = fitz.open(form_pdf_path)
        for page in doc:
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    try:
                        if widget.field_name in fields_to_fill:
                            widget.field_value = fields_to_fill[widget.field_name]
                            widget.update()
                    except Exception as e:
                        st.warning(f"⚠️ Could not fill '{widget.field_name}': {e}")

        # Save to temp file
        filled_pdf_path = os.path.join(tempfile.gettempdir(), "filled_form.pdf")
        doc.save(filled_pdf_path)
        doc.close()

        st.success("✅ PDF filled successfully.")
        with open(filled_pdf_path, "rb") as f:
            st.download_button("⬇️ Download Filled PDF", f, file_name="filled_form.pdf", mime="application/pdf")
