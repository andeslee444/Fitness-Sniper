/**
 * End-to-end booking test via Mariana Tek API.
 * Tests the new API-first adapter without browser automation for booking.
 *
 * Usage: npx tsx worker/src/test-booking.ts
 */

import dotenv from 'dotenv';
dotenv.config({ path: './worker/.env' });
import pg from 'pg';
import crypto from 'node:crypto';
import { MarianaTekAdapter } from './adapters/mariana-tek.js';

function decrypt(ciphertext: string, iv: string, authTag: string): string {
  const key = Buffer.from(process.env.ENCRYPTION_KEY!, 'hex');
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(iv, 'base64'), {
    authTagLength: 16,
  });
  decipher.setAuthTag(Buffer.from(authTag, 'base64'));
  let decrypted = decipher.update(ciphertext, 'base64', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}

async function main() {
  // 1. Fetch credentials
  console.log('📦 Fetching credentials...');
  const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  const { rows } = await pool.query(
    `SELECT encrypted_email, iv, auth_tag, encrypted_password, password_iv, password_auth_tag
     FROM studio_credentials WHERE studio_slug = 'barrys' LIMIT 1`,
  );
  if (rows.length === 0) { console.error('❌ No creds'); process.exit(1); }
  const cred = rows[0];
  const email = decrypt(cred.encrypted_email, cred.iv, cred.auth_tag);
  const password = decrypt(cred.encrypted_password, cred.password_iv, cred.password_auth_tag);
  console.log(`✅ Got credentials for ${email}`);
  await pool.end();

  // 2. Create adapter and authenticate
  console.log('\n🔑 Initializing adapter...');
  const adapter = new MarianaTekAdapter('barrys', { email, password }, {
    log: (step, detail) => console.log(`   [${step}] ${detail}`),
  });

  await adapter.init();

  // 3. Get today's classes
  console.log('\n📅 Fetching classes for Chelsea...');
  const classes = await adapter.getClasses('9594'); // Barry's Chelsea location API ID

  console.log(`   Found ${classes.length} classes:`);
  for (const c of classes.slice(0, 8)) {
    const ext = c as any;
    console.log(`   ${c.time} - ${c.className} (${c.instructor}) — ${ext.spotsAvailable ?? '?'} spots [id=${ext.classId}]`);
  }

  // 4. Get detail of a class with available spots
  const available = classes.filter(c => c.available);
  if (available.length > 0) {
    const target = available[0] as any;
    console.log(`\n🔍 Class detail for ${target.classId}: ${target.className}...`);
    const detail = await adapter.getClassDetail(target.classId);

    const spots = detail.layout?.spots || [];
    const openSpots = spots.filter(s => s.is_available);
    console.log(`   Layout: ${detail.layout?.name}`);
    console.log(`   Available: ${openSpots.length}/${spots.length}`);
    console.log(`   Spot types: ${[...new Set(spots.map(s => s.spot_type.name))].join(', ')}`);
    console.log(`   First 5 available:`);
    for (const s of openSpots.slice(0, 5)) {
      console.log(`     ${s.name} (${s.spot_type.name}, id=${s.id})`);
    }

    // 5. DRY RUN booking (don't actually book)
    console.log(`\n🎯 DRY RUN — would book:`);
    console.log(`   Class: ${target.className} at ${target.time}`);
    console.log(`   Spot: ${openSpots[0]?.name} (${openSpots[0]?.spot_type.name})`);
    console.log(`   API call: POST /me/reservations`);
    console.log(`   Body: { class_session: "${target.classId}", spot: ${openSpots[0]?.id}, reservation_type: "standard" }`);

    // To actually book, uncomment:
    // const result = await adapter.bookClass('9594', target.time, ['T-1', 'T-3', 'T-5']);
    // console.log(`\n📋 Result:`, result);
  }

  await adapter.close();
  console.log('\n✅ Test complete!');
}

main().catch(console.error);
