/**
 * Job Processor — executes a claimed booking job
 *
 * Flow: decrypt credentials → create adapter → execute booking → update status
 */

import { query } from '../db.js';
import { MarianaTekAdapter } from '../adapters/mariana-tek.js';
import { XponentialAdapter } from '../adapters/xponential.js';
import { decrypt } from '../crypto/credentials.js';
import { sendBookingEmail } from '../notifications/email.js';
import { STUDIOS } from '@fitness-sniper/shared';
import type { BookingJob, SnipeTarget, StudioCredential } from '@fitness-sniper/shared';

export class JobProcessor {
  private workerId: string;

  constructor(workerId: string) {
    this.workerId = workerId;
  }

  async process(job: BookingJob): Promise<void> {
    console.log(`[processor] Processing job ${job.id}`);

    // Update status to running
    await this.updateJobStatus(job.id, 'running');

    let adapter: MarianaTekAdapter | XponentialAdapter | null = null;

    try {
      // 1. Fetch target details
      const target = await this.getTarget(job.target_id);
      if (!target) {
        await this.failJob(job, 'Target not found');
        return;
      }

      // 2. Fetch and decrypt credentials
      const creds = await this.getDecryptedCredentials(job.user_id, target.studio_slug);
      if (!creds) {
        await this.failJob(job, `No credentials found for ${target.studio_slug}`);
        return;
      }

      // 3. Check studio is supported and create the right adapter
      const studioConfig = STUDIOS[target.studio_slug];
      if (!studioConfig) {
        await this.failJob(job, `Unknown studio: ${target.studio_slug}`);
        return;
      }

      const logFn = (step: string, detail: string) => {
        console.log(`[job:${job.id}] [${step}] ${detail}`);
      };

      // 4. Create adapter based on platform
      if (studioConfig.platform === 'mariana-tek') {
        adapter = new MarianaTekAdapter(target.studio_slug, creds, {
          log: logFn,
          screenshotDir: `/tmp/fitness-sniper/${job.id}`,
        });
      } else if (studioConfig.platform === 'xponential') {
        adapter = new XponentialAdapter(target.studio_slug, creds, { log: logFn });
      } else {
        await this.failJob(job, `Unsupported platform: ${studioConfig.platform}`);
        return;
      }

      await adapter.init();
      const result = await adapter.bookClass(
        target.location_id,
        target.time,
        target.preferred_spots || undefined,
      );

      // 5. Update job with result
      if (result.success) {
        await query(
          `UPDATE booking_jobs SET status = 'success', result_message = $1, spot_booked = $2, screenshot_url = $3 WHERE id = $4`,
          [result.message, result.spot || null, result.screenshotPath || null, job.id],
        );

        console.log(`[processor] Job ${job.id} SUCCESS: ${result.message}`);
      } else {
        await this.handleFailure(job, result.message);
      }

      // 6. Send notification
      const userEmail = await this.getUserEmail(job.user_id);
      if (userEmail) {
        await sendBookingEmail({
          to: userEmail,
          studioName: studioConfig.name,
          classTime: target.time,
          classDate: job.scheduled_for.split('T')[0],
          location: target.location_id,
          spot: result.spot || null,
          success: result.success,
          message: result.message,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`[processor] Job ${job.id} error:`, message);
      await this.handleFailure(job, message);
    } finally {
      if (adapter) {
        await adapter.close().catch(() => {});
      }
    }
  }

  private async getTarget(targetId: string): Promise<SnipeTarget | null> {
    const { rows } = await query<SnipeTarget>('SELECT * FROM snipe_targets WHERE id = $1', [targetId]);
    return rows[0] || null;
  }

  private async getDecryptedCredentials(
    userId: string,
    studioSlug: string,
  ): Promise<{ email: string; password: string } | null> {
    const { rows } = await query<StudioCredential>(
      'SELECT * FROM studio_credentials WHERE user_id = $1 AND studio_slug = $2',
      [userId, studioSlug],
    );

    if (!rows[0]) return null;
    const cred = rows[0];

    return {
      email: decrypt({ ciphertext: cred.encrypted_email, iv: cred.iv, authTag: cred.auth_tag }),
      password: decrypt({
        ciphertext: cred.encrypted_password,
        iv: cred.password_iv,
        authTag: cred.password_auth_tag,
      }),
    };
  }

  private async getUserEmail(userId: string): Promise<string | null> {
    const { rows } = await query<{ email: string }>('SELECT email FROM profiles WHERE id = $1', [userId]);
    return rows[0]?.email || null;
  }

  private async updateJobStatus(jobId: string, status: string): Promise<void> {
    await query('UPDATE booking_jobs SET status = $1 WHERE id = $2', [status, jobId]);
  }

  private async failJob(job: BookingJob, message: string): Promise<void> {
    await query(
      `UPDATE booking_jobs SET status = 'failed', result_message = $1 WHERE id = $2`,
      [message, job.id],
    );
    console.log(`[processor] Job ${job.id} FAILED: ${message}`);
  }

  private async handleFailure(job: BookingJob, message: string): Promise<void> {
    if (job.attempts < job.max_attempts) {
      // Reset to pending for retry
      await query(
        `UPDATE booking_jobs SET status = 'pending', claimed_by = NULL, claimed_at = NULL, result_message = $1 WHERE id = $2`,
        [`Attempt ${job.attempts} failed: ${message}`, job.id],
      );
      console.log(`[processor] Job ${job.id} will retry (attempt ${job.attempts}/${job.max_attempts})`);
    } else {
      await this.failJob(job, `All ${job.max_attempts} attempts failed. Last: ${message}`);
    }
  }
}
