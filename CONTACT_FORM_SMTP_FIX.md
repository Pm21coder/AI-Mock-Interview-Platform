# Fix Contact Form SMTP Error on Render

## Problem
The contact form shows: *"Email service is currently unavailable. Please configure the Gmail SMTP credentials..."*

## Solution: Add Gmail SMTP Credentials to Render

### Step 1: Get Gmail App Password

1. Go to: https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or your device)
3. Google will generate a **16-character password**
4. Copy this password (you'll need it in Step 2)

*Note: This requires 2-Factor Authentication enabled on your Gmail account. If you don't have it, enable it first at https://myaccount.google.com/security*

### Step 2: Add Environment Variables to Render

1. Go to your Render dashboard: https://dashboard.render.com/
2. Click on your backend service (`ai-mock-interview-backend-k09i` or `mock-interview-api-ug7h`)
3. Go to **Settings** → **Environment Variables**
4. Add these two variables:

| Key | Value |
|-----|-------|
| `GMAIL_USER` | your-email@gmail.com |
| `GMAIL_APP_PASSWORD` | your-16-character-app-password |

5. Click **Save** or **Deploy**

### Step 3: Test the Contact Form

1. Go to your app on mobile: https://rm-rust.vercel.app/contact
2. Fill out the contact form
3. Click "Send Message"
4. You should see a success toast: *"Message sent! We'll get back to you soon."*

---

## Troubleshooting

### "Email authentication failed"
- Verify the 16-character app password is correct (no spaces)
- Ensure 2-Factor Authentication is enabled on the Gmail account
- Double-check `GMAIL_USER` email address matches the account

### "Email service is not configured"
- Verify both `GMAIL_USER` and `GMAIL_APP_PASSWORD` are set in Render
- Check that they're saved (click Deploy after adding them)
- Wait 1-2 minutes for Render to apply the changes

### Still not working?
- Check Render logs for detailed error messages
- Verify the backend is running: https://ai-mock-interview-backend-k09i.onrender.com/health
- Try testing locally first (see step below)

---

## Test Locally (Desktop)

1. Create `.env` file in `mock-interview-platform/backend/`:
   ```
   GMAIL_USER=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-16-character-app-password
   ```

2. Start the backend: `python run.py`
3. Start the frontend: `npm run dev`
4. Go to: http://localhost:3000/contact
5. Test the contact form

If it works locally but not on Render, the issue is missing environment variables on Render deployment.

---

## Email Flow

- Contact form on frontend sends data to backend `/api/send-email`
- Backend uses Gmail SMTP to send two emails:
  1. **Admin notification** to `pramodmane09156@gmail.com`
  2. **User confirmation** to the user's provided email
- Both emails must send successfully for the form to return success

---

*Updated: Backend .env.example now includes GMAIL_USER and GMAIL_APP_PASSWORD examples*
