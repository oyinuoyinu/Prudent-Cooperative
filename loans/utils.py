from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Q
from .models import LoanApplication, LoanTenure
from members.models import Member
from savings.models import SavingsPlan, SavingsTransaction
from decimal import Decimal

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO
from django.conf import settings
import os

def check_loan_eligibility(member, loan_amount):
    """
    Check if a member is eligible for a loan based on multiple criteria.
    Returns all failed criteria reasons instead of stopping at the first failure.

    :param member: Member object
    :param loan_amount: Loan amount requested
    :return: dict with decision and all reasons
    """
    eligibility_status = {
        "membership_duration": {
            "status": "passed",
            "message": "Member meets minimum duration requirement."
        },
        "recent_savings": {
            "status": "passed",
            "message": "Member has recent savings activity."
        },
        "savings_balance": {
            "status": "passed",
            "message": "Member meets minimum savings balance requirement."
        }
    }

    # 1. Check membership duration (6 months minimum)
    six_months_ago = timezone.now().date() - timedelta(days=180)
    if member.join_date > six_months_ago:
        eligibility_status["membership_duration"] = {
            "status": "failed",
            "message": f"Member has only been active for {(timezone.now().date() - member.join_date).days} days. Minimum requirement is 180 days."
        }

    # 2. Check recent savings activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    savings_plans = SavingsPlan.objects.filter(user=member.user, status='active')

    recent_savings = SavingsTransaction.objects.filter(
        savings_plan__in=savings_plans,
        transaction_type='deposit',
        status='approved',
        transaction_date__gte=thirty_days_ago
    ).exists()

    if not recent_savings:
        eligibility_status["recent_savings"] = {
            "status": "failed",
            "message": "No approved savings deposits found in the last 30 days."
        }

    # 3. Check savings balance requirement (30% of loan amount)
    min_balance_required = Decimal('0.3') * loan_amount
    total_savings = savings_plans.aggregate(total=Sum('amount'))['total'] or 0

    if total_savings < min_balance_required:
        eligibility_status["savings_balance"] = {
            "status": "failed",
            "message": f"Total savings balance (₦{total_savings:,.2f}) is less than required 30% (₦{min_balance_required:,.2f}) of loan amount."
        }

    # Collect all failed criteria
    failed_criteria = [
        status["message"]
        for status in eligibility_status.values()
        if status["status"] == "failed"
    ]

    # Overall decision
    decision = "approved" if not failed_criteria else "rejected"

    return {
        "decision": decision,
        "status": eligibility_status,
        "failed_criteria": failed_criteria,
        "passed_criteria": [
            status["message"]
            for status in eligibility_status.values()
            if status["status"] == "passed"
        ],
        "total_criteria": len(eligibility_status),
        "failed_count": len(failed_criteria)
    }


def generate_receipt_pdf(loan_application):
    """Generate a PDF receipt for a loan application"""
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
    p.drawString(180, height - 100, "Loan Application Receipt")

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
    p.drawString(40, y, f"Receipt No: {loan_application.id}")

    # Date
    y -= 40
    p.setFont("Helvetica", 12)
    p.drawString(40, y, f"Date: {loan_application.application_date.strftime('%d-%m-%Y %H:%M')}")

    # Member info with background
    y -= 40
    full_name = loan_application.user.get_full_name() or loan_application.user.username
    p.setFillColor(colors.HexColor('#f8f9fa'))
    p.rect(35, y - 10, 250, 30, fill=True)
    p.setFillColor(colors.black)
    p.drawString(40, y, f"Member: {full_name}")

    # Payment details header
    y -= 60
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(primary_color)
    p.drawString(40, y, "Payment Details")
    p.setLineWidth(1)
    p.line(40, y - 5, 550, y - 5)

    # Reset color and font
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 12)

    # Details table
    y -= 40
    p.drawString(40, y, "Description")
    p.drawString(400, y, "Amount")

    # Payment info with alternating background
    y -= 30
    p.setFillColor(colors.HexColor('#f8f9fa'))
    p.rect(35, y - 10, 520, 30, fill=True)
    p.setFillColor(colors.black)
    p.drawString(40, y, "Loan Application Fee")
    p.drawString(400, y, f"₦{loan_application.application_fee:,.2f}")

    # Status with custom styling
    y -= 40
    status_color = colors.green if loan_application.status == 'approved' else colors.red
    p.setFillColor(status_color)
    p.drawString(40, y, "Status:")
    p.drawString(400, y, loan_application.status.upper())

    # Total amount with special styling
    y -= 50
    p.setFillColor(primary_color)
    p.setLineWidth(2)
    p.line(35, y + 15, 550, y + 15)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "Total Amount Paid")
    p.drawString(400, y, f"₦{loan_application.application_fee:,.2f}")

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

