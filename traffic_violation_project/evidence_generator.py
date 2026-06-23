"""
evidence_generator.py - Professional Evidence Generation
Includes police-style challan (e-challan) PDF generation
"""

import sys
from typing import Optional

import cv2
import numpy as np
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("reportlab not installed. Install with: pip install reportlab")


class EvidenceGenerator:
    """
    Generate police-style evidence reports
    """

    # Color mapping per violation type (BGR)
    VIOLATION_COLORS = {
        'NO HELMET':       (0, 0, 255),    # Red
        'NO_HELMET':       (0, 0, 255),
        'NO SEATBELT':     (0, 200, 255),  # Yellow-orange
        'NO_SEATBELT':     (0, 200, 255),
        'TRIPLE RIDING':   (255, 0, 255),  # Magenta
        'TRIPLE_RIDING':   (255, 0, 255),
        'RED LIGHT':       (0, 0, 220),    # Dark red
        'RED_LIGHT':       (0, 0, 220),
        'WRONG SIDE':      (255, 50, 0),   # Blue-orange
        'WRONG_SIDE':      (255, 50, 0),
        'STOP LINE':       (0, 180, 0),    # Green
        'STOP_LINE':       (0, 180, 0),
        'STOP LINE CROSSING':       (0, 180, 0),
        'STOP_LINE_CROSSING':       (0, 180, 0),
        'RED SIGNAL OVERRAKING':     (0, 0, 220),   # Dark red
        'RED_SIGNAL_OVERRAKING':     (0, 0, 220),
        'ILLEGAL PARKING': (0, 140, 255),  # Orange
        'ILLEGAL_PARKING': (0, 140, 255),
    }

    def __init__(self, output_dir='evidence'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def draw_annotations(self, image: np.ndarray, violations: list) -> np.ndarray:
        """Minimal annotation: 2px border + small label pill above each violation box."""
        annotated = image.copy()

        for violation in violations:
            bbox = violation.get('bbox') or violation.get('box')
            if not bbox or len(bbox) < 4:
                continue

            x1, y1, x2, y2 = map(int, bbox[:4])
            vtype = violation.get('type') or violation.get('violation_type', 'UNKNOWN')
            confidence = violation.get('confidence', 0.0)

            color = self.VIOLATION_COLORS.get(vtype, (255, 255, 255))

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            label = f"{vtype.replace('_', ' ')}: {confidence:.0%}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            label_y = y1 - 5
            if label_y - text_h - 4 < 0:
                label_y = y2 + 5

            cv2.rectangle(annotated,
                         (x1, label_y - text_h - 4),
                         (x1 + text_w + 8, label_y + 2),
                         color, -1)
            cv2.putText(annotated, label, (x1 + 4, label_y - baseline),
                       font, font_scale, (255, 255, 255), thickness)

        return annotated

    def generate_evidence_card(self, image, violation, vehicle_info=None,
                               plate_info=None, all_violations=None):
        """
        Generate a complete evidence card with bounding-box annotations.

        Args:
            image: path string or BGR numpy array
            violation: primary violation dict (used for the info panel)
            vehicle_info: optional dict with 'type', 'color'
            plate_info: unused (kept for API compatibility)
            all_violations: list of all violation dicts to annotate; if None,
                            only the primary violation is annotated

        Returns:
            Path to the saved evidence card image
        """
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Could not read image: {image}")

        # Draw bounding-box annotations for all violations
        violations_to_draw = all_violations if all_violations is not None else [violation]
        annotated_image = self.draw_annotations(image, violations_to_draw)

        h, w = annotated_image.shape[:2]
        card_h = h + 280
        border = 15
        card_w = max(w + 2 * border, 800)

        card = np.ones((card_h, card_w, 3), dtype=np.uint8) * 245

        card[border:border + h, border:border + w] = annotated_image

        self._draw_header(card, violation, card_w)
        self._draw_info_panel(card, violation, vehicle_info, plate_info, h, card_w)
        self._draw_footer(card, card_h, card_w)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        vtype = violation.get('type', violation.get('violation_type', 'violation')).replace(' ', '_')
        filename = f"evidence_{vtype}_{timestamp}.jpg"
        output_path = os.path.join(self.output_dir, filename)
        cv2.imwrite(output_path, card)

        return output_path

    def _draw_header(self, card, violation, card_w):
        """Draw evidence card header"""
        cv2.rectangle(card, (0, 0), (card_w, 60), (20, 40, 80), -1)
        cv2.putText(
            card, "TRAFFIC VIOLATION EVIDENCE REPORT",
            (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
        )
        cv2.putText(
            card, "Government of India - Traffic Enforcement System",
            (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 220), 1
        )

    def _draw_info_panel(self, card, violation, vehicle_info, plate_info, img_h, card_w):
        """Draw violation information panel"""
        y_start = img_h + 30
        panel_x = 20

        vtype = violation.get('type', violation.get('violation_type', 'UNKNOWN'))
        confidence = violation.get('confidence', 0.0)
        plate = violation.get('plate_text', violation.get('plateText', 'N/A'))

        info_lines = [
            f"VIOLATION TYPE: {vtype}",
            f"CONFIDENCE: {confidence * 100:.1f}%",
            f"LICENSE PLATE: {plate}",
            f"TIMESTAMP: {violation.get('timestamp', datetime.now().isoformat())}",
            f"VEHICLE TYPE: {vehicle_info.get('type', 'N/A') if vehicle_info else 'N/A'}",
            f"VEHICLE COLOR: {vehicle_info.get('color', 'N/A') if vehicle_info else 'N/A'}"
        ]

        for i, line in enumerate(info_lines):
            y = y_start + i * 25
            cv2.putText(
                card, line,
                (panel_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1
            )

    def _draw_footer(self, card, card_h, card_w):
        """Draw footer with timestamp and ID"""
        cv2.rectangle(card, (0, card_h - 30), (card_w, card_h), (40, 40, 40), -1)

        evidence_id = f"EV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cv2.putText(
            card, f"Evidence ID: {evidence_id} | Generated: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}",
            (20, card_h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1
        )

    def generate_pdf_report(self, violations, output_path='report.pdf'):
        """
        Generate a PDF report using ReportLab
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch

            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30
            )
            story.append(Paragraph("Traffic Violation Report", title_style))
            story.append(Spacer(1, 0.25 * inch))

            story.append(Paragraph(
                f"Total Violations: {len(violations)}", styles['Normal']
            ))
            story.append(Paragraph(
                f"Date: {datetime.now().strftime('%d %B %Y, %H:%M')}", styles['Normal']
            ))
            story.append(Spacer(1, 0.25 * inch))

            data = [['#', 'Type', 'Plate', 'Confidence', 'Timestamp']]
            for i, v in enumerate(violations, 1):
                data.append([
                    str(i),
                    v.get('type', v.get('violation_type', 'Unknown')),
                    v.get('plate_text', v.get('plateText', 'N/A')),
                    f"{v.get('confidence', 0) * 100:.1f}%",
                    str(v.get('timestamp', ''))[:19]
                ])

            table = Table(data, colWidths=[0.5 * inch, 2 * inch, 1.5 * inch, 1 * inch, 2 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(table)
            doc.build(story)
            logger.info(f"PDF report generated: {output_path}")
            return output_path

        except ImportError:
            logger.error("ReportLab not installed. Install with: pip install reportlab")
            return None
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return None

    def generate_challan(self, violation: dict, offender: Optional[dict] = None,
                         output_dir: Optional[str] = None) -> Optional[str]:
        """
        Generate a police-style e-challan (traffic ticket) PDF

        Args:
            violation: Violation details dict
            offender: Offender details (name, address, license_no, etc.)
            output_dir: Output directory for the challan PDF

        Returns:
            Path to generated challan PDF, or None on failure
        """
        if not HAS_REPORTLAB:
            logger.error("reportlab required for challan generation")
            return None

        output_dir = output_dir or os.path.join(self.output_dir, 'challans')
        os.makedirs(output_dir, exist_ok=True)

        challan_id = f"CH{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
        vtype = violation.get('type', violation.get('violation_type', 'UNKNOWN'))
        plate = violation.get('plate_text', violation.get('plateText', 'N/A'))
        timestamp = violation.get('timestamp', datetime.now().isoformat())
        confidence = violation.get('confidence', 0.0)
        fine_amount = self._get_fine_amount(vtype)

        filename = f"challan_{vtype.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(output_dir, filename)

        try:
            doc = SimpleDocTemplate(output_path, pagesize=A4,
                                    topMargin=20*mm, bottomMargin=20*mm,
                                    leftMargin=15*mm, rightMargin=15*mm)
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle('ChallanTitle', parent=styles['Heading1'],
                                         fontSize=18, alignment=1, spaceAfter=10,
                                         textColor=colors.HexColor('#1a1a2e'))
            subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                            fontSize=9, alignment=1, spaceAfter=20,
                                            textColor=colors.HexColor('#555555'))
            header_style = ParagraphStyle('Header', parent=styles['Normal'],
                                          fontSize=10, spaceAfter=4,
                                          textColor=colors.HexColor('#333333'))
            value_style = ParagraphStyle('Value', parent=styles['Normal'],
                                         fontSize=10, spaceAfter=4,
                                         textColor=colors.HexColor('#000000'))
            section_style = ParagraphStyle('Section', parent=styles['Heading2'],
                                           fontSize=13, spaceBefore=15, spaceAfter=8,
                                           textColor=colors.HexColor('#1a1a2e'))
            fine_style = ParagraphStyle('Fine', parent=styles['Normal'],
                                        fontSize=14, spaceAfter=4,
                                        textColor=colors.HexColor('#cc0000'))

            story = []

            story.append(Paragraph("E - C H A L L A N", title_style))
            story.append(Paragraph("Government of India - Traffic Enforcement System", subtitle_style))
            story.append(Paragraph(f"Challan ID: {challan_id}", subtitle_style))

            story.append(Spacer(1, 10))
            story.append(Paragraph("<hr/>", styles['Normal']))
            story.append(Spacer(1, 10))

            story.append(Paragraph("Offence Details", section_style))

            offence_data = [
                ['Violation Type', vtype],
                ['Date & Time', timestamp[:19]],
                ['Location', violation.get('location', 'Bangalore, KA')],
                ['Confidence', f"{confidence * 100:.1f}%"],
                ['License Plate', plate],
            ]

            if offender:
                offence_data.insert(3, ['Vehicle Type', offender.get('vehicle_type', 'N/A')])
                offence_data.insert(4, ['Vehicle Color', offender.get('vehicle_color', 'N/A')])

            ot = Table(offence_data, colWidths=[120, 320])
            ot.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(ot)

            story.append(Spacer(1, 10))

            if offender:
                story.append(Paragraph("Offender Details", section_style))
                off_data = [
                    ['Name', offender.get('name', 'N/A')],
                    ['Address', offender.get('address', 'N/A')],
                    ['License No.', offender.get('license_no', 'N/A')],
                    ['Phone', offender.get('phone', 'N/A')],
                ]
                off_table = Table(off_data, colWidths=[120, 320])
                off_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(off_table)
                story.append(Spacer(1, 10))

            story.append(Paragraph("Fine Details", section_style))
            fine_data = [
                ['Fine Amount', f"Rs. {fine_amount:,}/-"],
                ['Payment Deadline', (datetime.now() + timedelta(days=15)).strftime('%d %b %Y')],
                ['Payment Mode', 'Online / Bank / Traffic Court'],
            ]
            ft = Table(fine_data, colWidths=[120, 320])
            ft.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 0), (1, 0), 12),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.HexColor('#cc0000')),
            ]))
            story.append(ft)

            story.append(Spacer(1, 20))
            story.append(Paragraph("<hr/>", styles['Normal']))
            story.append(Spacer(1, 10))

            story.append(Paragraph(
                "<b>Note:</b> Please pay the fine within 15 days. "
                "Failure to comply may result in additional penalties or legal action.",
                styles['Normal']
            ))
            story.append(Spacer(1, 5))
            story.append(Paragraph(
                "<b>Dispute:</b> If you wish to contest this challan, please appear before "
                "the designated Traffic Court within 7 days.",
                styles['Normal']
            ))

            story.append(Spacer(1, 20))
            issuing_data = [
                ['Issuing Officer', violation.get('reviewed_by', 'Traffic Enforcement')],
                ['Issued At', datetime.now().strftime('%d %b %Y, %H:%M')],
                ['Department', 'Traffic Management Center, Bengaluru'],
            ]
            issuing_table = Table(issuing_data, colWidths=[120, 320])
            issuing_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#666666')),
            ]))
            story.append(issuing_table)

            doc.build(story)
            logger.info(f"Challan generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Challan generation error: {e}")
            return None

    def generate_evidence_preview(self, image: np.ndarray, violations: list) -> dict:
        """Generate preview data with annotations and fine calculation"""
        annotated = self.draw_annotations(image, violations)
        total_fine = sum(self._get_fine_amount(v.get('type', v.get('violation_type', ''))) for v in violations)
        return {
            'violations': violations,
            'total_fine': total_fine,
            'violation_count': len(violations),
            'severity': self._calculate_severity(violations),
            'annotated_image': annotated.tolist() if isinstance(annotated, np.ndarray) else None
        }

    def _calculate_severity(self, violations: list) -> str:
        severities = {
            'NO_HELMET': 2, 'NO HELMET': 2,
            'NO_SEATBELT': 2, 'NO SEATBELT': 2,
            'TRIPLE_RIDING': 3, 'TRIPLE RIDING': 3,
            'WRONG_SIDE': 4, 'WRONG SIDE': 4,
            'STOP_LINE': 3, 'STOP LINE': 3,
            'RED_LIGHT': 5, 'RED LIGHT': 5,
            'ILLEGAL_PARKING': 1, 'ILLEGAL PARKING': 1,
        }
        max_sev = max((severities.get(v.get('type', v.get('violation_type', '')), 0) for v in violations), default=0)
        if max_sev >= 4: return 'critical'
        if max_sev >= 3: return 'high'
        if max_sev >= 2: return 'medium'
        return 'low'

    def _get_fine_amount(self, violation_type: str) -> int:
        fines = {
            'NO_HELMET': 1000,
            'NO HELMET': 1000,
            'NO_SEATBELT': 1000,
            'NO SEATBELT': 1000,
            'TRIPLE_RIDING': 1500,
            'TRIPLE RIDING': 1500,
            'RED_LIGHT': 5000,
            'RED LIGHT': 5000,
            'WRONG_SIDE': 2000,
            'WRONG SIDE': 2000,
            'STOP_LINE': 500,
            'STOP LINE': 500,
            'ILLEGAL_PARKING': 500,
            'ILLEGAL PARKING': 500,
            'SPEEDING': 2000,
            'NO_LICENSE': 5000,
            'NO LICENSE': 5000,
        }
        return fines.get(violation_type.upper(), 1000)
