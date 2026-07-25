from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_template_pdf() -> None:
    output_dir = Path(__file__).resolve().parents[3] / "fixtures" / "pdf"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "basic-registration-v1.pdf"

    print(f"Generating template PDF at {pdf_path}...")

    # Letter is 612 x 792 points
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter

    # Draw header with styling
    c.setFillColor(colors.HexColor("#10172A"))  # Dark navy slate
    c.rect(0, height - 80, width, 80, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, height - 50, "AI Form Assistant")

    c.setFont("Helvetica", 10)
    c.drawString(width - 220, height - 48, "Document Type: Basic Registration")
    c.drawString(width - 220, height - 60, "Version: 1.0 (Phase 8 Predefined)")

    # Draw a clean border line
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(1)
    c.line(40, height - 100, width - 40, height - 100)

    # Content Area Header
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 130, "Applicant Personal Information")

    # Form Fields definition
    fields = [
        {"name": "first_name", "label": "First Name:", "y": height - 180},
        {"name": "last_name", "label": "Last Name:", "y": height - 230},
        {
            "name": "date_of_birth",
            "label": "Date of Birth (JJJJ-MM-TT):",
            "y": height - 280,
        },
        {"name": "email", "label": "Email Address:", "y": height - 330},
        {"name": "country", "label": "Country of Residence:", "y": height - 380},
        {"name": "marital_status", "label": "Marital Status:", "y": height - 430},
    ]

    form = c.acroForm

    for field in fields:
        # Draw label
        c.setFillColor(colors.HexColor("#334155"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, field["y"] + 4, field["label"])

        # Create AcroForm text field using the modern ReportLab API
        form.textfield(
            name=field["name"],
            x=200,
            y=field["y"] - 6,
            width=300,
            height=24,
            value="",
            fillColor=colors.HexColor("#F8FAFC"),
            borderColor=colors.HexColor("#CBD5E1"),
            textColor=colors.HexColor("#0F172A"),
            borderWidth=1,
            fontSize=10,
        )

    # Footer line and text
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.line(40, 100, width - 40, 100)

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 8)
    c.drawString(40, 80, "This is an automatically generated document complete check.")
    c.drawRightString(width - 40, 80, "Page 1 of 1")

    c.save()
    print("Pre-defined PDF template created successfully.")


if __name__ == "__main__":
    generate_template_pdf()
