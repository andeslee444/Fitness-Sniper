# Fitness Sniper 🎯

Auto-book competitive fitness classes the moment they open. Never miss a spot at Barry's, Aarmy, SLT, and more.

## Features

- **Multi-Studio Support** — Barry's, Aarmy, SLT, and other popular studios
- **Auto-Booking** — Snipe classes as soon as booking windows open
- **Schedule Monitoring** — Track when new classes are added
- **Waitlist Management** — Auto-join waitlists when classes are full
- **Notifications** — Get alerts when bookings succeed or fail

## Architecture

```
fitness-sniper/
├── worker/           # Booking daemon & scrapers
├── web/              # Web interface
└── packages/shared/  # Shared types & utilities
```

## Setup

```bash
# Install dependencies
npm install

# Run the worker (booking daemon)
npm run worker

# Run the web interface
npm run web:dev
```

## Configuration

Copy `.env.example` to `.env` and configure:
- Studio credentials
- Notification settings (Telegram, email, etc.)
- Target classes and times

## How It Works

1. Configure your target studios and class preferences
2. Worker monitors booking windows
3. Auto-books when slots open (typically 24-48h before class)
4. Sends notification on success/failure

## Status

Active development. Currently supports Barry's and Aarmy.

## License

Private
