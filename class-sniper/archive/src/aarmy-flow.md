# Aarmy Booking Flow - Verified 2026-02-13

## Platform
**Mariana Tek** (same as Barry's!)
- Main site: `aarmy.com`
- Booking portal: `mt.aarmy.com`
- Auth: `aarmy.marianatek.com`

## URLs
- Homepage: `https://aarmy.com/`
- Booking: `https://mt.aarmy.com/index.html?_mt=%2Fschedule%2Fdaily`
- Direct schedule: Navigate via "book your first HQ session" link

## NYC Locations
- **Chelsea (A23)** - 140 West 23rd St
- **NoHo** - 636 Broadway

## Booking Flow

### 1. Login
Two options:
- From aarmy.com: Click "Log in" → "Log in with Mariana Tek"
- Direct: Go to `aarmy.marianatek.com/auth/login/`

### 2. Navigate to Schedule
- Click "book your first HQ session"
- Or go to `mt.aarmy.com`

### 3. Select Location
Click location button in iframe:
- "Chelsea (A23)"
- "NoHo"

### 4. View Classes
Same Mariana Tek interface as Barry's:
- Day navigation (Mon-Sun)
- Filter buttons (Instructor, Class Type, Rooms)
- Class cards with time, instructor, type
- "RESERVE" button for available classes

### 5. Reserve
- Click RESERVE → Spot selection
- Login required if not authenticated
- Select spot → Confirm

## Selectors

### Main Site (aarmy.com)
```
link "Log in"           # Opens login modal
button "Log in with Mariana Tek"  # OAuth to Mariana Tek
menuitem "avatar AL"    # Indicates logged in
link "book your first HQ session"  # Goes to booking
```

### Booking Portal (mt.aarmy.com)
Same Mariana Tek selectors as Barry's:
```
iframe                  # Main content iframe
button "{Location}"     # Location selection
button "Reserve"        # Reserve button (via link in Barry's)
button "Available Spot" # Spot selection
```

## Credentials Tested
- Email: andes.leelee@gmail.com
- Password: Ilovebex823
- ✅ Login successful!
- ✅ Schedule visible
- ✅ RESERVE buttons found

## Key Findings

1. **Same Platform as Barry's** - Can use unified adapter
2. **OAuth via Mariana Tek** - Same auth flow
3. **Different booking URL** - `mt.aarmy.com` vs `barrysbootcamp.marianaiframes.com`
4. **Simpler iframe** - Not embedded in another site like Barry's

## Class Schedule Sample (Chelsea, Feb 13)
- 6:00 AM - Full Body (Yavuz) - Bootcamp
- 7:00 AM - Glutes & Arms (Yavuz) - Bootcamp
- 8:15 AM - Full Body (Claire) - Bootcamp
- 5:00 PM - Full Body: Breakup Anthems (Anjali) - Bootcamp ✅ RESERVE
- 6:00 PM - Full Body (Mya) - Bootcamp ✅ RESERVE
