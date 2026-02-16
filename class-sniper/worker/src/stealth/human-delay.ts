/**
 * Human-like interaction delays and typing
 *
 * Adds randomization to all browser actions to mimic real user behavior
 * and avoid bot detection.
 */

import { Page, Frame } from 'playwright';

/**
 * Random delay between min and max milliseconds
 */
export function humanDelay(min = 3000, max = 8000): Promise<void> {
  const ms = Math.floor(Math.random() * (max - min + 1)) + min;
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Short delay for between-action pauses
 */
export function shortDelay(min = 500, max = 1500): Promise<void> {
  return humanDelay(min, max);
}

/**
 * Add ±20% jitter to a base delay
 */
export function randomJitter(baseMs: number): Promise<void> {
  const jitter = baseMs * 0.2;
  const ms = baseMs + (Math.random() * 2 - 1) * jitter;
  return new Promise((resolve) => setTimeout(resolve, Math.max(0, ms)));
}

/**
 * Type text with random per-character delay (50-150ms)
 */
export async function humanType(
  target: Page | Frame,
  selector: string,
  text: string,
): Promise<void> {
  await target.click(selector);
  await shortDelay(200, 400);

  for (const char of text) {
    await target.type(selector, char, { delay: 0 });
    const charDelay = Math.floor(Math.random() * 100) + 50;
    await new Promise((resolve) => setTimeout(resolve, charDelay));
  }
}

/**
 * Click with slight position offset to appear human
 */
export async function humanClick(
  target: Page | Frame,
  selector: string,
): Promise<void> {
  const element = await target.$(selector);
  if (!element) throw new Error(`Element not found: ${selector}`);

  const box = await element.boundingBox();
  if (!box) throw new Error(`Element not visible: ${selector}`);

  // Random offset within the element bounds
  const x = box.x + box.width * (0.3 + Math.random() * 0.4);
  const y = box.y + box.height * (0.3 + Math.random() * 0.4);

  await (target as Page).mouse?.move(x, y, { steps: 5 });
  await shortDelay(100, 300);
  await (target as Page).mouse?.click(x, y);
}
