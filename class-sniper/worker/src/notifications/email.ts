/**
 * Email notifications via Resend
 */

import { Resend } from 'resend';

let resend: Resend | null = null;

function getResend(): Resend {
  if (!resend) {
    const key = process.env.RESEND_API_KEY;
    if (!key) throw new Error('RESEND_API_KEY not set');
    resend = new Resend(key);
  }
  return resend;
}

export interface BookingNotification {
  to: string;
  studioName: string;
  classTime: string;
  classDate: string;
  location: string;
  spot: string | null;
  success: boolean;
  message: string;
}

export async function sendBookingEmail(notification: BookingNotification): Promise<void> {
  const { to, studioName, classTime, classDate, location, spot, success, message } = notification;

  const status = success ? 'Booked' : 'Failed';
  const emoji = success ? '✅' : '❌';

  try {
    await getResend().emails.send({
      from: 'Class Sniper <noreply@classsniper.app>',
      to: [to],
      subject: `${emoji} ${status}: ${studioName} ${classTime} on ${classDate}`,
      html: `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
          <h2 style="margin: 0 0 16px;">${emoji} Booking ${status}</h2>
          <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px 0; color: #666;">Studio</td><td style="padding: 8px 0; font-weight: 600;">${studioName}</td></tr>
            <tr><td style="padding: 8px 0; color: #666;">Date</td><td style="padding: 8px 0; font-weight: 600;">${classDate}</td></tr>
            <tr><td style="padding: 8px 0; color: #666;">Time</td><td style="padding: 8px 0; font-weight: 600;">${classTime}</td></tr>
            <tr><td style="padding: 8px 0; color: #666;">Location</td><td style="padding: 8px 0; font-weight: 600;">${location}</td></tr>
            ${spot ? `<tr><td style="padding: 8px 0; color: #666;">Spot</td><td style="padding: 8px 0; font-weight: 600;">${spot}</td></tr>` : ''}
          </table>
          ${message ? `<p style="margin: 16px 0 0; color: #666; font-size: 14px;">${message}</p>` : ''}
          <hr style="margin: 24px 0; border: none; border-top: 1px solid #eee;" />
          <p style="margin: 0; color: #999; font-size: 12px;">Class Sniper</p>
        </div>
      `,
    });
  } catch (err) {
    console.error('[email] Failed to send notification:', err);
  }
}
