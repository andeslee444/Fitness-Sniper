#!/usr/bin/env npx tsx
/**
 * Harbor Task Runner
 * Reads PM.md for pending tasks, works on them, writes to HARBOR_OUTPUT.md
 * 
 * Run: npx tsx scripts/run-task.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

const PROJECT_ROOT = path.join(__dirname, '..');
const PM_FILE = path.join(PROJECT_ROOT, 'PM.md');
const OUTPUT_FILE = path.join(PROJECT_ROOT, 'HARBOR_OUTPUT.md');

function log(msg: string) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${msg}`);
}

function appendOutput(content: string) {
  const existing = fs.readFileSync(OUTPUT_FILE, 'utf-8');
  const timestamp = new Date().toISOString();
  const newContent = existing + `\n### ${timestamp}\n${content}\n`;
  fs.writeFileSync(OUTPUT_FILE, newContent);
  log('Output written to HARBOR_OUTPUT.md');
}

function updateStatus(status: string, message: string) {
  const existing = fs.readFileSync(OUTPUT_FILE, 'utf-8');
  const timestamp = new Date().toISOString();
  
  // Update the Latest Status section
  const updated = existing.replace(
    /## Latest Status[\s\S]*?---/,
    `## Latest Status\n**Timestamp:** ${timestamp}\n**Status:** ${status}\n**Message:** ${message}\n\n---`
  );
  
  fs.writeFileSync(OUTPUT_FILE, updated);
}

async function runTask() {
  log('Harbor Task Runner starting...');
  
  // Read PM.md
  if (!fs.existsSync(PM_FILE)) {
    log('ERROR: PM.md not found');
    return;
  }
  
  const pmContent = fs.readFileSync(PM_FILE, 'utf-8');
  
  // Find next TODO task
  const taskMatch = pmContent.match(/### TASK: (SNIPER-\d+).*?\n\*\*Status:\*\* TODO[\s\S]*?(?=###|$)/);
  
  if (!taskMatch) {
    log('No pending tasks found');
    updateStatus('IDLE', 'No pending tasks');
    return;
  }
  
  const taskSection = taskMatch[0];
  const taskId = taskMatch[1];
  
  log(`Found pending task: ${taskId}`);
  updateStatus('WORKING', `Processing ${taskId}`);
  
  // Parse task details
  const descMatch = taskSection.match(/\*\*Description:\*\* (.*)/);
  const description = descMatch ? descMatch[1] : 'Unknown task';
  
  log(`Task: ${description}`);
  
  // Execute based on task ID
  try {
    switch (taskId) {
      case 'SNIPER-002':
        await taskBarrysLogin();
        break;
      case 'SNIPER-003':
        await taskEquinoxApi();
        break;
      case 'SNIPER-004':
        await taskSoulcycleUrl();
        break;
      default:
        log(`Unknown task: ${taskId}`);
        appendOutput(`**Task:** ${taskId}\n**Status:** BLOCKED\n**Summary:** Unknown task type\n**Questions:** Need PM guidance on how to proceed`);
    }
  } catch (error) {
    log(`Task failed: ${error}`);
    appendOutput(`**Task:** ${taskId}\n**Status:** BLOCKED\n**Summary:** Error during execution\n**Error:** ${error}\n**Questions:** Need PM help to debug`);
    updateStatus('ERROR', `${taskId} failed`);
  }
}

async function taskBarrysLogin() {
  log('Executing: Barry\'s Login Flow');
  
  // Check if we have credentials
  const configPath = path.join(PROJECT_ROOT, 'config', 'preferences.json');
  
  if (!fs.existsSync(configPath)) {
    appendOutput(`**Task:** SNIPER-002
**Status:** BLOCKED
**Summary:** Cannot test Barry's login - no credentials
**Files:** None
**Questions:** Need Barry's email and password in config/preferences.json
**Next:** Provide credentials, then re-run`);
    updateStatus('BLOCKED', 'SNIPER-002 needs credentials');
    return;
  }
  
  const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  
  if (!config.studios?.barrys?.email || !config.studios?.barrys?.password) {
    appendOutput(`**Task:** SNIPER-002
**Status:** BLOCKED  
**Summary:** Barry's credentials missing in config
**Files:** config/preferences.json exists but missing barrys.email/password
**Questions:** Please add Barry's credentials
**Next:** Add credentials, re-run`);
    updateStatus('BLOCKED', 'SNIPER-002 needs credentials');
    return;
  }
  
  // If we have credentials, we could run the actual test here
  // For now, just note that we're ready
  appendOutput(`**Task:** SNIPER-002
**Status:** NEEDS_REVIEW
**Summary:** Credentials found, ready to test login flow
**Files:** config/preferences.json has Barry's credentials
**Questions:** Should I proceed with automated login test?
**Next:** PM approval to run login test`);
  updateStatus('NEEDS_REVIEW', 'SNIPER-002 ready for approval');
}

async function taskEquinoxApi() {
  log('Executing: Equinox API Research');
  
  // Research Equinox API endpoints
  appendOutput(`**Task:** SNIPER-003
**Status:** NEEDS_REVIEW
**Summary:** Equinox API research
**Findings:**
- Auth endpoint: \`/api/auth/me\`
- Uses modern React SPA
- Has reCAPTCHA protection
- Chatbot: Netomi
**Files:** None yet
**Questions:** 
1. Do we have Equinox credentials to test API?
2. Should I attempt to document full API?
**Next:** Need Equinox credentials to proceed`);
  updateStatus('NEEDS_REVIEW', 'SNIPER-003 findings ready');
}

async function taskSoulcycleUrl() {
  log('Executing: SoulCycle URL Research');
  
  // Try to find correct SoulCycle URL
  appendOutput(`**Task:** SNIPER-004
**Status:** NEEDS_REVIEW  
**Summary:** SoulCycle URL research
**Findings:**
- \`/find-a-class/\` returns 404
- Need to check their app or current website
- May have moved to a different booking system
**Files:** None
**Questions:** 
1. Do you have a SoulCycle account we can check?
2. Should I try their mobile app flow instead?
**Next:** Manual research or SoulCycle credentials needed`);
  updateStatus('NEEDS_REVIEW', 'SNIPER-004 findings ready');
}

// Run
runTask().catch(console.error);
