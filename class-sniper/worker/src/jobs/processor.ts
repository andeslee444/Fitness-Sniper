/**
 * Job Processor — executes a claimed booking job
 *
 * Flow: decrypt credentials → launch stealth browser → execute booking → update status
 */

import { SupabaseClient } from '@supabase/supabase-js';
import { MarianaTekAdapter } from '../adapters/mariana-tek.js';
import { decrypt } from '../crypto/credentials.js';
import { sendBookingEmail } from '../notifications/email.js';
import { STUDIOS } from '@class-sniper/shared';
import type { BookingJob, SnipeTarget, StudioCredential } from '@class-sniper/shared';

export class JobProcessor {
  private supabase: SupabaseClient;
  private workerId: string;

  constructor(supabase: SupabaseClient, workerId: string) {
    this.supabase = supabase;
    this.workerId = workerId;
  }

  async process(job: BookingJob): Promise<void> {
    console.log(`[processor] Processing job ${job.id}`);

    // Update status to running
    await this.updateJobStatus(job.id, 'running');

    let adapter: MarianaTekAdapter | null = null;

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

      // 3. Check studio is supported
      const studioConfig = STUDIOS[target.studio_slug];
      if (!studioConfig || studioConfig.platform !== 'mariana-tek') {
        await this.failJob(job, `Unsupported studio: ${target.studio_slug}`);
        return;
      }

      // 4. Launch adapter and book
      adapter = new MarianaTekAdapter(target.studio_slug, creds, {
        log: (step, detail) => {
          console.log(`[job:${job.id}] [${step}] ${detail}`);
        },
        screenshotDir: `/tmp/class-sniper/${job.id}`,
      });

      await adapter.init();
      const result = await adapter.bookClass(
        target.location_id,
        target.time,
        target.preferred_spots || undefined,
      );

      // 5. Update job with result
      if (result.success) {
        await this.supabase
          .from('booking_jobs')
          .update({
            status: 'success',
            result_message: result.message,
            spot_booked: result.spot || null,
            screenshot_url: result.screenshotPath || null,
          })
          .eq('id', job.id);

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
    const { data } = await this.supabase
      .from('snipe_targets')
      .select('*')
      .eq('id', targetId)
      .single();
    return data;
  }

  private async getDecryptedCredentials(
    userId: string,
    studioSlug: string,
  ): Promise<{ email: string; password: string } | null> {
    const { data } = await this.supabase
      .from('studio_credentials')
      .select('*')
      .eq('user_id', userId)
      .eq('studio_slug', studioSlug)
      .single();

    if (!data) return null;
    const cred = data as StudioCredential;

    return {
      email: decrypt({ ciphertext: cred.encrypted_email, iv: cred.iv, authTag: cred.auth_tag }),
      password: decrypt({ ciphertext: cred.encrypted_password, iv: cred.iv, authTag: cred.auth_tag }),
    };
  }

  private async getUserEmail(userId: string): Promise<string | null> {
    // Use admin API to get user email from auth.users
    const { data } = await this.supabase.auth.admin.getUserById(userId);
    return data?.user?.email || null;
  }

  private async updateJobStatus(jobId: string, status: string): Promise<void> {
    await this.supabase
      .from('booking_jobs')
      .update({ status })
      .eq('id', jobId);
  }

  private async failJob(job: BookingJob, message: string): Promise<void> {
    await this.supabase
      .from('booking_jobs')
      .update({
        status: 'failed',
        result_message: message,
      })
      .eq('id', job.id);
    console.log(`[processor] Job ${job.id} FAILED: ${message}`);
  }

  private async handleFailure(job: BookingJob, message: string): Promise<void> {
    if (job.attempts < job.max_attempts) {
      // Reset to pending for retry
      await this.supabase
        .from('booking_jobs')
        .update({
          status: 'pending',
          claimed_by: null,
          claimed_at: null,
          result_message: `Attempt ${job.attempts} failed: ${message}`,
        })
        .eq('id', job.id);
      console.log(`[processor] Job ${job.id} will retry (attempt ${job.attempts}/${job.max_attempts})`);
    } else {
      await this.failJob(job, `All ${job.max_attempts} attempts failed. Last: ${message}`);
    }
  }
}
