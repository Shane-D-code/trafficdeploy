from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_pdf_report(violations, stats, output_path=None):
    if output_path is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(reports_dir / f"traffic_report_{timestamp}.pdf")
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph("Traffic Violation Detection Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}", styles["Normal"]
        )
    )
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Summary", styles["Heading2"]))
    elements.append(
        Paragraph(f"Total Violations: {stats.get('total', 0)}", styles["Normal"])
    )
    elements.append(
        Paragraph(
            f"Vehicles Detected: {stats.get('total_vehicles', 0)}", styles["Normal"]
        )
    )
    elements.append(Spacer(1, 12))
    if violations:
        elements.append(Paragraph("Detected Violations", styles["Heading2"]))
        data = [["#", "Type", "Confidence", "Plate"]]
        for i, v in enumerate(violations, 1):
            data.append(
                [
                    str(i),
                    v.get("type", ""),
                    f"{v.get('confidence', 0):.2f}",
                    v.get("plate_text") or "N/A",
                ]
            )
        t = Table(data, colWidths=[30, 120, 80, 120])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        elements.append(t)
    else:
        elements.append(Paragraph("No violations detected.", styles["Normal"]))
    if stats.get("by_type"):
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Violations by Type", styles["Heading2"]))
        type_data = [["Type", "Count"]]
        for vt, count in stats["by_type"].items():
            type_data.append([vt, str(count)])
        t2 = Table(type_data, colWidths=[200, 100])
        t2.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        elements.append(t2)
    doc.build(elements)
    return output_path


if __name__ == "__main__":
    test_violations = [
        {"type": "NO HELMET", "confidence": 0.92, "plate_text": "KA01AB1234"},
        {"type": "NO SEATBELT", "confidence": 0.74, "plate_text": "DL10C5678"},
    ]
    test_stats = {
        "total": 2,
        "total_vehicles": 2,
        "by_type": {"NO HELMET": 1, "NO SEATBELT": 1},
    }
    path = generate_pdf_report(test_violations, test_stats)
    print(f"Report generated: {path}")
