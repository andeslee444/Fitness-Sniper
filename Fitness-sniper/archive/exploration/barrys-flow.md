# Barry's Booking Flow - Verified 2026-02-13

## Platform
**Mariana Tek** (same as Aarmy)
- Iframe: `barrysbootcamp.marianaiframes.com`
- Auth: `barrysbootcamp.marianatek.com`

## URLs
- Schedule: `https://www.barrys.com/schedule/{studio}`
- Example: `https://www.barrys.com/schedule/noho`

## NYC Studios
- Brooklyn Heights
- Chelsea
- East 64th
- East 86th
- Long Island City
- NoHo
- Park Ave South
- Tribeca

## Booking Flow

### 1. Navigate to Schedule
```
https://www.barrys.com/book-now/
→ Select USA → New York → NYC → Studio
```

### 2. View Classes
- Schedule loads in Mariana Tek iframe
- Shows class time, instructor, type
- "Reserve" button for available classes
- "Join Waitlist" for full classes

### 3. Select Spot
Click Reserve → Shows floor plan with spots:
- Available spots are clickable
- Must log in to complete

### 4. Login (if not authenticated)
- Email + Password fields
- Standard Mariana Tek auth
- Returns to spot selection after login

### 5. Complete Reservation
- Select spot
- Confirm booking
- Uses class credits from account

## Selectors Tested

### Main Page
```
iframe.visible  # Main Mariana Tek iframe
```

### Schedule View (in iframe)
```
button "Reserve"     # Reserve class
link "Join Waitlist" # Full class
button "{Date}"      # Date navigation
```

### Spot Selection (in iframe)
```
button "Available Spot"  # Click to select
button "Log In"          # Opens login
```

### Login Form
```
textbox "Email"     # Email input
textbox "Password"  # Password input
button "Log in"     # Submit
```

## Credentials Tested
- Email: user@example.com
- Password: example-password
- ✅ Login successful!

## Key Insights
1. Both Barry's and Aarmy use Mariana Tek
2. Can potentially share auth session between them
3. Schedule accessible without login
4. Login required only when reserving
5. Browser automation works through iframe.visible selector
