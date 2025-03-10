from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from io import BytesIO
from django.conf import settings
from django.utils import timezone
from django.contrib.staticfiles.finders import find
import os

def generate_savings_receipt_pdf(transaction):
    """Generate a PDF receipt for a savings transaction"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Define colors
    primary_color = colors.HexColor('#dc3545')  # Bootstrap red
    secondary_color = colors.HexColor('#6c757d')  # Bootstrap secondary gray

    # Add company logo
    logo_path = find('images/logo.jpeg')  # This will find the logo in any static directory
    if logo_path:
        p.drawImage(logo_path, 40, height - 120, width=100, height=80, mask='auto')

    # Add receipt header
    p.setFillColor(primary_color)
    p.setFont("Helvetica-Bold", 28)
    p.drawString(180, height - 100, "Transaction Receipt")

    # Add decorative elements
    p.setStrokeColor(primary_color)
    p.setLineWidth(2)
    p.line(40, height - 160, width - 40, height - 160)

    # Reset color for main content
    p.setFillColor(colors.black)

    # Add receipt details with improved styling
    y = height - 200  # Starting y position for details

    # Receipt number with background
    p.setFillColor(colors.HexColor('#f8f9fa'))  # Light gray background
    p.rect(35, y - 10, 250, 30, fill=True)
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, f"Receipt No: {transaction.reference_number}")

    # Date
    y -= 40
    p.setFont("Helvetica", 12)
    p.drawString(40, y, f"Date: {transaction.transaction_date.strftime('%d-%m-%Y %H:%M')}")

    # Member info with background
    y -= 40
    user = transaction.savings_plan.user
    full_name = f"{user.first_name} {user.last_name}".strip() or user.username
    p.setFillColor(colors.HexColor('#f8f9fa'))
    p.rect(35, y - 10, 250, 30, fill=True)
    p.setFillColor(colors.black)
    p.drawString(40, y, f"Member: {full_name}")

    # Transaction details header
    y -= 60
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(primary_color)
    p.drawString(40, y, "Transaction Details")
    p.setLineWidth(1)
    p.line(40, y - 5, 550, y - 5)

    # Reset color and font
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 12)

    # Details table
    y -= 40
    p.drawString(40, y, "Description")
    p.drawString(400, y, "Amount")

    # Transaction info with alternating background
    y -= 30
    transaction_type = "Deposit" if transaction.transaction_type == 'deposit' else "Withdrawal"
    p.setFillColor(colors.HexColor('#f8f9fa'))
    p.rect(35, y - 10, 520, 30, fill=True)
    p.setFillColor(colors.black)
    p.drawString(40, y, f"Savings {transaction_type}")
    p.drawString(400, y, f"₦{transaction.amount:,.2f}")

    # Payment method if exists
    if hasattr(transaction, 'payment_method'):
        y -= 30
        p.drawString(40, y, "Payment Method:")
        p.drawString(400, y, transaction.payment_method.upper())

    # Status with custom styling
    y -= 40
    status_color = colors.green if transaction.status == 'approved' else colors.red
    p.setFillColor(status_color)
    p.drawString(40, y, "Status:")
    p.drawString(400, y, transaction.status.upper())

    # Current balance with special styling
    y -= 50
    p.setFillColor(primary_color)
    p.setLineWidth(2)
    p.line(35, y + 15, 550, y + 15)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Current Balance")
    p.drawString(400, y, f"₦{transaction.savings_plan.amount:,.2f}")

    # Footer with design
    p.setFillColor(colors.HexColor('#f8f9fa'))
    p.rect(0, 0, width, 120, fill=True)
    p.setFillColor(secondary_color)
    p.setFont("Helvetica", 10)
    p.drawString(40, 100, "This is a computer-generated receipt. No signature required.")
    p.drawString(40, 80, f"Generated on: {timezone.now().strftime('%d-%m-%Y %H:%M:%S')}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer