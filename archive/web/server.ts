/**
 * Class Sniper Web UI - Configuration Dashboard
 * 
 * Run: npx ts-node web/server.ts
 * Access: http://localhost:3847
 * 
 * Created: 2026-02-13
 */

import express from 'express';
import cors from 'cors';
import * as fs from 'fs';
import * as path from 'path';

const app = express();
const PORT = 3847;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ============================================================
// CONFIG PATHS
// ============================================================

const CONFIG_PATH = path.join(__dirname, '../config/sniper-config.json');
const LOG_PATH = path.join(__dirname, '../logs/sniper.log');

// ============================================================
// TYPES
// ============================================================

interface ClassTarget {
  id: string;
  studio: 'barrys' | 'aarmy';
  location: string;
  dayOfWeek: number;
  time: string;
  seatPreference: 'front' | 'middle' | 'back' | 'any';
  preferredSpots?: string[];
  enabled: boolean;
  lastChecked?: string;
  lastBooked?: string;
}

interface SniperConfig {
  credentials: {
    barrys?: { email: string; password: string };
    aarmy?: { email: string; password: string };
  };
  targets: ClassTarget[];
  settings: {
    dryRun: boolean;
    notifyOnBook: boolean;
    notifyPhone?: string;
  };
}

// ============================================================
// STUDIO DATA
// ============================================================

const STUDIOS = {
  barrys: {
    name: "Barry's Bootcamp",
    locations: [
      { id: 'noho', name: 'NoHo', address: '636 Broadway' },
      { id: 'chelsea', name: 'Chelsea', address: '305 W 27th St' },
      { id: 'tribeca', name: 'Tribeca', address: '141 Watts St' },
      { id: 'brooklyn-heights', name: 'Brooklyn Heights', address: '194 Joralemon St' },
      { id: 'east-64th', name: 'East 64th', address: '213 E 64th St' },
      { id: 'east-86th', name: 'East 86th', address: '1526 2nd Ave' },
      { id: 'long-island-city', name: 'Long Island City', address: '29-11 Queens Plaza N' },
      { id: 'park-ave-south', name: 'Park Ave South', address: '393 Park Ave S' }
    ],
    times: ['5:00 AM', '6:00 AM', '7:15 AM', '8:30 AM', '9:45 AM', '11:00 AM', '12:15 PM', '4:00 PM', '5:15 PM', '6:30 PM', '7:45 PM']
  },
  aarmy: {
    name: 'Aarmy',
    locations: [
      { id: 'chelsea', name: 'Chelsea (A23)', address: '140 West 23rd St' },
      { id: 'noho', name: 'NoHo', address: '636 Broadway' }
    ],
    times: ['6:00 AM', '7:00 AM', '8:15 AM', '12:00 PM', '5:00 PM', '6:00 PM', '7:00 PM']
  }
};

// Spot mappings by preference
const SPOT_PREFERENCES = {
  front: ['F-1', 'F-3', 'F-5', 'F-7', 'F-2', 'F-4', 'F-6', 'F-8'],
  middle: ['F-9', 'F-10', 'F-11', 'F-12', 'F-13', 'F-14', 'F-15', 'F-16'],
  back: ['T-1', 'T-3', 'T-5', 'T-7', 'T-2', 'T-4', 'T-6', 'T-8', 'T-9', 'T-10'],
  any: [] // Will select first available
};

// ============================================================
// HELPERS
// ============================================================

function loadConfig(): SniperConfig {
  if (!fs.existsSync(CONFIG_PATH)) {
    const defaultConfig: SniperConfig = {
      credentials: {},
      targets: [],
      settings: { dryRun: true, notifyOnBook: true }
    };
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(defaultConfig, null, 2));
    return defaultConfig;
  }
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
}

function saveConfig(config: SniperConfig): void {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
}

function generateTargetId(target: Partial<ClassTarget>): string {
  return `${target.studio}-${target.location}-${target.dayOfWeek}-${target.time?.replace(/[: ]/g, '')}`;
}

// ============================================================
// API ROUTES
// ============================================================

// Get studios and locations
app.get('/api/studios', (req, res) => {
  res.json(STUDIOS);
});

// Get spot preferences
app.get('/api/spot-preferences', (req, res) => {
  res.json(SPOT_PREFERENCES);
});

// Get current config
app.get('/api/config', (req, res) => {
  const config = loadConfig();
  // Don't expose passwords
  const safeConfig = {
    ...config,
    credentials: {
      barrys: config.credentials.barrys ? { email: config.credentials.barrys.email, hasPassword: true } : null,
      aarmy: config.credentials.aarmy ? { email: config.credentials.aarmy.email, hasPassword: true } : null
    }
  };
  res.json(safeConfig);
});

// Get all targets
app.get('/api/targets', (req, res) => {
  const config = loadConfig();
  res.json(config.targets);
});

// Add a target
app.post('/api/targets', (req, res) => {
  const config = loadConfig();
  const { studio, location, dayOfWeek, time, seatPreference } = req.body;
  
  const newTarget: ClassTarget = {
    id: generateTargetId({ studio, location, dayOfWeek, time }),
    studio,
    location,
    dayOfWeek: parseInt(dayOfWeek),
    time,
    seatPreference: seatPreference || 'any',
    preferredSpots: SPOT_PREFERENCES[seatPreference as keyof typeof SPOT_PREFERENCES] || [],
    enabled: true
  };
  
  // Check for duplicate
  const existing = config.targets.find(t => t.id === newTarget.id);
  if (existing) {
    return res.status(400).json({ error: 'Target already exists' });
  }
  
  config.targets.push(newTarget);
  saveConfig(config);
  res.json(newTarget);
});

// Update a target
app.put('/api/targets/:id', (req, res) => {
  const config = loadConfig();
  const targetIndex = config.targets.findIndex(t => t.id === req.params.id);
  
  if (targetIndex === -1) {
    return res.status(404).json({ error: 'Target not found' });
  }
  
  const updates = req.body;
  if (updates.seatPreference) {
    updates.preferredSpots = SPOT_PREFERENCES[updates.seatPreference as keyof typeof SPOT_PREFERENCES] || [];
  }
  
  config.targets[targetIndex] = { ...config.targets[targetIndex], ...updates };
  saveConfig(config);
  res.json(config.targets[targetIndex]);
});

// Delete a target
app.delete('/api/targets/:id', (req, res) => {
  const config = loadConfig();
  config.targets = config.targets.filter(t => t.id !== req.params.id);
  saveConfig(config);
  res.json({ success: true });
});

// Toggle target enabled/disabled
app.post('/api/targets/:id/toggle', (req, res) => {
  const config = loadConfig();
  const target = config.targets.find(t => t.id === req.params.id);
  
  if (!target) {
    return res.status(404).json({ error: 'Target not found' });
  }
  
  target.enabled = !target.enabled;
  saveConfig(config);
  res.json(target);
});

// Update settings
app.put('/api/settings', (req, res) => {
  const config = loadConfig();
  config.settings = { ...config.settings, ...req.body };
  saveConfig(config);
  res.json(config.settings);
});

// Update credentials
app.put('/api/credentials/:studio', (req, res) => {
  const config = loadConfig();
  const { email, password } = req.body;
  const studio = req.params.studio as 'barrys' | 'aarmy';
  
  config.credentials[studio] = { email, password };
  saveConfig(config);
  res.json({ success: true });
});

// Get recent logs
app.get('/api/logs', (req, res) => {
  if (!fs.existsSync(LOG_PATH)) {
    return res.json([]);
  }
  const logs = fs.readFileSync(LOG_PATH, 'utf-8').split('\n').filter(Boolean).slice(-50);
  res.json(logs);
});

// Run state for live updates
let runState: {
  isRunning: boolean;
  currentStep: number;
  steps: { step: number; status: string; detail: string; timestamp: string }[];
  targetId: string | null;
} = {
  isRunning: false,
  currentStep: 0,
  steps: [],
  targetId: null
};

// Get current run state
app.get('/api/run/status', (req, res) => {
  res.json(runState);
});

// Start a test run
app.post('/api/run/start', async (req, res) => {
  const { targetId } = req.body;
  
  if (runState.isRunning) {
    return res.status(400).json({ error: 'A run is already in progress' });
  }
  
  const config = loadConfig();
  const target = config.targets.find(t => t.id === targetId);
  
  if (!target) {
    return res.status(404).json({ error: 'Target not found' });
  }
  
  // Initialize run state
  runState = {
    isRunning: true,
    currentStep: 0,
    steps: [],
    targetId
  };
  
  res.json({ success: true, message: 'Run started' });
});

// Update run step (called by sniper process)
app.post('/api/run/step', (req, res) => {
  const { step, status, detail } = req.body;
  
  runState.currentStep = step;
  runState.steps.push({
    step,
    status,
    detail,
    timestamp: new Date().toISOString()
  });
  
  if (status === 'complete' && step === 5) {
    runState.isRunning = false;
  }
  
  res.json({ success: true });
});

// Stop a run
app.post('/api/run/stop', (req, res) => {
  runState.isRunning = false;
  runState.steps.push({
    step: runState.currentStep,
    status: 'stopped',
    detail: 'Run stopped by user',
    timestamp: new Date().toISOString()
  });
  res.json({ success: true });
});

// ============================================================
// START SERVER
// ============================================================

app.listen(PORT, () => {
  console.log(`🎯 Class Sniper UI running at http://localhost:${PORT}`);
});
