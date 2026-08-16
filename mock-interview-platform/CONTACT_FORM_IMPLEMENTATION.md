# Cookie Consent & Contact Form Implementation

## Summary

This update adds two new features to the MockInterview AI app:

### 1. Cookie Consent Banner
- **Location**: Bottom of every page
- **Features**:
  - Accept/Decline buttons
  - Persistent storage in localStorage
  - Dark mode support
  - Only shows once per user
  - Links to privacy policy (when available)

**Files Modified**:
- `frontend/src/components/CookieBanner.js` (new)
- `frontend/src/app/layout.js` - Added CookieBanner import and rendering

### 2. Contact Us Form
- **Location**: `/contact` route
- **Features**:
  - Name, Email, Subject, Message fields
  - Email validation
  - Dark mode support
  - Confirmation emails to user
  - Admin notifications to `pramodmane09156@gmail.com`
  - Toast notifications for user feedback
  - Fallback mode for when email service is unavailable

**Files Created**:
- `frontend/src/app/contact/page.js` - Contact form page
- `frontend/src/app/api/contact/route.js` - Next.js API route
- `backend/app/services/email_service.py` - Flask email service
- `EMAIL_SETUP.md` - Email configuration guide

**Files Modified**:
- `frontend/src/components/Navigation.js` - Added Contact link
- `backend/app/__init__.py` - Registered email service blueprint

## Usage

### For Users

1. **Cookies Banner**:
   - Appears on first visit
   - Click "Accept" to enable analytics and tracking
   - Click "Decline" to disable tracking
   - Choice is saved in localStorage and won't show again

2. **Contact Form**:
   - Navigate to `/contact` via the navigation menu
   - Fill in name, email, subject, and message
   - Submit the form
   - Receive automatic confirmation email
   - Admin receives notification email

### For Administrators

To enable email functionality:

1. Set up Gmail App Password:
   - Enable 2-Factor Authentication on your Gmail account
   - Visit https://myaccount.google.com/apppasswords
   - Generate an app password

2. Configure Environment Variables:
   ```bash
   # Backend (.env or system variables)
   GMAIL_USER=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-16-char-app-password
   
   # Frontend (.env.local)
   NEXT_PUBLIC_BACKEND_URL=http://localhost:5000
   ```

3. Restart the backend server for changes to take effect

## Features

### Cookie Banner
- ✅ Persistent storage using localStorage
- ✅ Dark mode support with automatic styling
- ✅ Clean, accessible design
- ✅ Touch-friendly button sizing
- ✅ Responsive layout (mobile and desktop)

### Contact Form
- ✅ Full form validation
- ✅ Email validation with regex
- ✅ Loading state while sending
- ✅ Error and success notifications
- ✅ Responsive design (mobile and desktop)
- ✅ Dark mode support
- ✅ Automatic confirmation emails
- ✅ Admin notifications
- ✅ Fallback mode (form accepts submissions even if email fails)

## Email Flow

```
User Submits Form
    ↓
Frontend validates input
    ↓
POST to /api/contact
    ↓
Backend tries to send via Gmail
    ├─ Success: Send confirmation + admin email
    └─ Failure: Log error but return success (graceful fallback)
    ↓
Frontend shows success message
```

## Styling

Both the cookie banner and contact form are styled with:
- Tailwind CSS classes
- Dark mode support using `dark:` prefix
- Smooth transitions
- Accessible colors and contrast
- Touch-friendly interaction targets (min 48px)

## Testing

To test locally:

1. **Cookie Banner**:
   ```bash
   npm run dev
   # Open http://localhost:3000
   # Banner should appear at the bottom
   # Click Accept/Decline to test persistence
   # Refresh page - banner should not reappear
   ```

2. **Contact Form**:
   ```bash
   # Start backend: python run.py
   # Start frontend: npm run dev
   # Go to http://localhost:3000/contact
   # Fill form and submit
   # Check server logs for submission details
   ```

## Production Deployment

### Email Service in Production

For production deployments, consider using a dedicated email service:

- **SendGrid** (Recommended)
  - Free tier: 100 emails/day
  - Update `email_service.py` to use SendGrid API

- **Mailgun**
  - Free tier: 5,000 emails/month
  - Professional approach

- **AWS SES**
  - Pay-as-you-go
  - Integrates well with AWS infrastructure

### Environment Variables

Set these in your production environment:
- `GMAIL_USER` - Sender email address
- `GMAIL_APP_PASSWORD` - App-specific password (for Gmail)
- `NEXT_PUBLIC_BACKEND_URL` - Backend API URL

## Troubleshooting

### Cookie Banner Not Appearing
- Check browser console for errors
- Verify localStorage is enabled
- Clear browser cache and localStorage

### Contact Form Not Working
- Check browser console for network errors
- Verify backend is running (`http://localhost:5000`)
- Check backend logs for email errors
- Ensure environment variables are set

### Emails Not Sending
- Verify Gmail credentials are correct
- Check that 2FA is enabled on Gmail account
- Verify app password (not regular password)
- Check backend logs for SMTP errors
- Ensure port 465 (SMTP) is not blocked by firewall

## File Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── contact/
│   │   │   └── page.js (new)
│   │   ├── api/
│   │   │   └── contact/
│   │   │       └── route.js (new)
│   │   └── layout.js (updated)
│   └── components/
│       ├── CookieBanner.js (new)
│       └── Navigation.js (updated)

backend/
├── app/
│   ├── services/
│   │   └── email_service.py (new)
│   └── __init__.py (updated)

EMAIL_SETUP.md (new)
```

## Future Enhancements

- Add more email providers support
- Implement rate limiting for form submissions
- Add CAPTCHA for spam prevention
- Store contact submissions in database
- Add admin dashboard to view submissions
- Implement email templates
