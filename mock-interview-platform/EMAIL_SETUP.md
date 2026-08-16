# Email Configuration for Contact Form

To enable the contact form email functionality, you need to set up Gmail SMTP credentials.

## Setup Instructions

### 1. Enable 2-Factor Authentication on Gmail
1. Go to your Google Account: https://myaccount.google.com/
2. Click on "Security" in the left sidebar
3. Enable "2-Step Verification"

### 2. Create an App Password
1. Go to: https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or your device)
3. Google will generate a 16-character password
4. Copy this password

### 3. Set Environment Variables

**For Backend (.env or environment variables):**
```bash
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
```

**For Frontend (.env.local):**
```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:5000
```

### 4. Test the Setup
1. Start the backend: `python run.py`
2. Start the frontend: `npm run dev`
3. Navigate to `/contact`
4. Fill out the form and submit
5. Verify that emails are received at `pramodmane09156@gmail.com`

## Email Features

- **Contact Form Submission**: Sends notification to `pramodmane09156@gmail.com`
- **User Confirmation**: Automatically sends confirmation email to the user
- **Error Handling**: Gracefully handles email service failures
- **Fallback Mode**: Form submission succeeds even if email service is unavailable

## Troubleshooting

### "Email authentication failed"
- Ensure you've enabled 2-Factor Authentication
- Verify the app password is correct (16 characters)
- Check that the email address is correct

### "Connection refused"
- Ensure the backend server is running on port 5000
- Check that `NEXT_PUBLIC_BACKEND_URL` is correct in frontend

### Emails not being sent
- Check server console logs for error messages
- Verify Gmail credentials in environment variables
- Ensure both GMAIL_USER and GMAIL_APP_PASSWORD are set

## Production Deployment

For production, use a dedicated email service:
- **SendGrid**: https://sendgrid.com/
- **Mailgun**: https://www.mailgun.com/
- **AWS SES**: https://aws.amazon.com/ses/

Update the backend email service to use the preferred provider.
