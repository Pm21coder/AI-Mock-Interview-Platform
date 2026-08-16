"""Email service for handling contact form submissions."""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify

email_bp = Blueprint('email', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


def send_email(to_email, subject, html_content, from_email=None):
    """
    Send an email using Gmail SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        from_email: Sender email (defaults to env variable)
    
    Returns:
        tuple: (success, message)
    """
    try:
        sender_email = from_email or os.getenv('GMAIL_USER')
        sender_password = os.getenv('GMAIL_APP_PASSWORD')

        logger.info(f"Attempting to send email from {sender_email} to {to_email} with subject: {subject}")

        if not sender_email or not sender_password:
            logger.error("Email service not configured: missing GMAIL_USER or GMAIL_APP_PASSWORD")
            return False, "Email service not configured"

        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = sender_email
        message['To'] = to_email

        part = MIMEText(html_content, 'html')
        message.attach(part)

        logger.info("Connecting to Gmail SMTP server...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            logger.info("Connected to Gmail SMTP server")
            server.login(sender_email, sender_password)
            logger.info(f"Logged in as {sender_email}")
            server.sendmail(sender_email, to_email, message.as_string())
            logger.info(f"Email sent successfully from {sender_email} to {to_email}")

        return True, "Email sent successfully"

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Email authentication failed: {str(e)}")
        return False, "Email authentication failed. Check credentials."
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}", exc_info=True)
        return False, f"Error sending email: {str(e)}"


@email_bp.route('/send-email', methods=['POST'])
def send_contact_email():
    """Handle contact form email submission."""
    try:
        import sys
        print("[EMAIL_DEBUG] Received contact form submission", flush=True)
        sys.stdout.flush()
        logger.info("Received contact form submission")
        data = request.get_json()
        
        if not data:
            print("[EMAIL_DEBUG] No JSON data provided", flush=True)
            logger.warning("No JSON data provided in contact form request")
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message_text = data.get('message', '').strip()
        
        print(f"[EMAIL_DEBUG] Form data - Name: {name}, Email: {email}, Subject: {subject}", flush=True)
        logger.info(f"Contact form data - Name: {name}, Email: {email}, Subject: {subject}")
        
        # Validate required fields
        if not all([name, email, subject, message_text]):
            print("[EMAIL_DEBUG] Missing required fields", flush=True)
            logger.warning("Contact form missing required fields")
            return jsonify({'error': 'Missing required fields'}), 400
        
        sender_email = os.getenv('GMAIL_USER')
        sender_password = os.getenv('GMAIL_APP_PASSWORD')
        if not sender_email or not sender_password:
            print(f"[EMAIL_DEBUG] Email not configured - sender_email={sender_email}, has_password={bool(sender_password)}", flush=True)
            logger.error("GMAIL_USER or GMAIL_APP_PASSWORD not configured")
            return jsonify({
                'error': 'Email service is not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD in the backend environment before sending contact form messages.'
            }), 503

        # Prepare recipient email
        recipient_email = 'pramodmane09156@gmail.com'
        print(f"[EMAIL_DEBUG] Preparing to send to admin: {recipient_email}", flush=True)
        logger.info(f"Preparing to send contact form email to admin: {recipient_email}")
        
        # Create HTML email content for admin
        admin_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2563eb;">New Contact Form Submission</h2>
                <p><strong>Name:</strong> {html_escape(name)}</p>
                <p><strong>Email:</strong> {html_escape(email)}</p>
                <p><strong>Subject:</strong> {html_escape(subject)}</p>
                <p><strong>Message:</strong></p>
                <p>{html_escape(message_text).replace(chr(10), '<br>')}</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;"><em>Reply to: {html_escape(email)}</em></p>
            </body>
        </html>
        """
        
        # Create HTML email content for user confirmation
        user_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2563eb;">Thank you for contacting us!</h2>
                <p>Hi {html_escape(name)},</p>
                <p>We've received your message and will get back to you as soon as possible.</p>
                <p><strong>Your message:</strong></p>
                <p>{html_escape(message_text).replace(chr(10), '<br>')}</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p>Best regards,<br><strong>MockInterview AI Team</strong></p>
            </body>
        </html>
        """
        
        # Send email to admin
        logger.info("Sending admin notification email")
        success, msg = send_email(
            recipient_email,
            f'New Contact Form: {subject}',
            admin_html,
            from_email=sender_email,
        )
        
        if not success:
            logger.error(f"Failed to send admin email: {msg}")
            return jsonify({
                'error': f'Could not send admin email: {msg}'
            }), 503
        
        logger.info("Admin email sent successfully")
        
        # Send confirmation email to user
        logger.info(f"Sending confirmation email to user at {email}")
        success, msg = send_email(
            email,
            'We received your message - MockInterview AI',
            user_html,
            from_email=sender_email,
        )
        
        if not success:
            logger.error(f"Failed to send user confirmation email: {msg}")
            return jsonify({
                'error': f'Could not send confirmation email: {msg}'
            }), 503
        
        logger.info("User confirmation email sent successfully")
        return jsonify({
            'success': True,
            'message': 'Thank you for your message. We will get back to you soon.'
        }), 200
    
    except Exception as e:
        logger.error(f"Error in send_contact_email: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to process contact form'}), 500


def html_escape(text):
    """Escape HTML special characters."""
    if not text:
        return ''
    escape_table = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }
    return ''.join(escape_table.get(c, c) for c in text)
