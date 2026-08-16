export async function POST(request) {
  try {
    const { name, email, subject, message } = await request.json();

    if (!name || !email || !subject || !message) {
      return new Response(JSON.stringify({ error: 'Missing required fields' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return new Response(JSON.stringify({ error: 'Invalid email address' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Prepare email content
    const emailContent = {
      to: 'pramodmane09156@gmail.com',
      subject: `New Contact Form: ${subject}`,
      name,
      email,
      subject: subject,
      message: message,
    };

    // Try to send via backend API if available
    try {
      const backendResponse = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'}/api/send-email`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(emailContent),
        }
      );

      const responseText = await backendResponse.text();
      let backendData = {};
      try {
        backendData = responseText ? JSON.parse(responseText) : {};
      } catch {
        backendData = {};
      }

      if (backendResponse.ok) {
        return new Response(JSON.stringify({ success: true, message: 'Email sent successfully' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      return new Response(
        JSON.stringify({
          error: backendData.error || 'Email service is currently unavailable. Please try again later.',
        }),
        {
          status: backendResponse.status || 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    } catch (backendError) {
      console.error('Backend email service not available:', backendError);
      return new Response(
        JSON.stringify({
          error: 'Email service is currently unavailable. Please configure the Gmail SMTP credentials or try again later.',
        }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  } catch (error) {
    console.error('Contact form error:', error);
    return new Response(JSON.stringify({ error: 'Failed to process request' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
