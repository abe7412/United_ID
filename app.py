import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import re
import tempfile
import os
import zipfile

st.set_page_config(page_title="Muqeem Form Filler", layout="centered")

st.title("UNITED ID APPLICATION- Muqeem")
st.markdown("Upload **Muqeem PDFs** and a **form PDF** with fillable fields. The app will generate one filled form per Muqeem.")

st.subheader("Operator Input")

po = st.text_input("PO Number")

start_date = st.date_input("Contract Start Date")
end_date = st.date_input("Contract End Date")

# Extract day/month/year for PDF fields
start_day = f"{start_date.day:02d}"
start_month = f"{start_date.month:02d}"
start_year = str(start_date.year)

end_day = f"{end_date.day:02d}"
end_month = f"{end_date.month:02d}"
end_year = str(end_date.year)


# ---------- Upload PDFs ----------
muqeem_files = st.file_uploader("📄 Upload Muqeem PDFs", type="pdf", accept_multiple_files=True)
form_file = st.file_uploader("📋 Upload Form PDF (fillable)", type="pdf")

# ---------- Helper: Extract Muqeem Data ----------
def extract_muqeem_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

    data = {}
    name_match_1 = re.search(r"Translated Name\s+([A-Z\s\-']+?)\s+(Birth Date|Nationality|Iqama|Passport|Gender|Issue Date)", text)
    name_match_2 = re.search(r"Name\s+([A-Z\s\-']+?)\s+(Birth Date|Nationality|Iqama|Passport|Gender|Issue Date)", text)
    data["Name"] = name_match_1.group(1).strip() if name_match_1 else (
        name_match_2.group(1).strip() if name_match_2 else "Not found"
    )
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
if muqeem_files and form_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as form_temp:
        form_temp.write(form_file.read())
        form_pdf_path = form_temp.name

    filled_files = []

    for idx, muqeem_file in enumerate(muqeem_files):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as muqeem_temp:
            muqeem_temp.write(muqeem_file.read())
            muqeem_pdf_path = muqeem_temp.name

        data = extract_muqeem_data(muqeem_pdf_path)

        if not data.get("Name") or not data.get("Iqama"):
            st.warning(f"⚠️ Required fields missing in Muqeem file {muqeem_file.name}. Skipped.")
            continue

        # Dummy fixed fields
        # ----------- Operator Input -----------

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
                        st.warning(f"Could not fill '{widget.field_name}' for {muqeem_file.name}: {e}")

        filled_path = os.path.join(tempfile.gettempdir(), f"filled_{idx}_{data['Iqama']}.pdf")
        doc.save(filled_path)
        doc.close()
        filled_files.append(filled_path)

    if filled_files:
        # ZIP all PDFs
        zip_path = os.path.join(tempfile.gettempdir(), "filled_forms.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for path in filled_files:
                zipf.write(path, arcname=os.path.basename(path))

        st.success("✅ All Muqeem PDFs processed and forms filled.")
        with open(zip_path, "rb") as zf:
            st.download_button("⬇️ Download All Filled PDFs (ZIP)", zf, file_name="filled_forms.zip", mime="application/zip")
