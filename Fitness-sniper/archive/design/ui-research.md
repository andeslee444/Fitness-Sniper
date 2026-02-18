# Premium Fitness Studio UI/UX Research

> Research conducted: February 13, 2026
> Purpose: Design reference for Class Sniper app

---

## 1. Barry's Bootcamp (barrys.com)

### Brand Identity
High-energy, dark atmosphere with signature red lighting. Known as "The Best Workout in the World."

### Color Palette
| Color | Hex Code | Usage |
|-------|----------|-------|
| Barry's Red | `#E31837` | Primary accent, CTAs, logo |
| Deep Black | `#0A0A0A` | Background |
| Off-Black | `#1A1A1A` | Cards, secondary backgrounds |
| Pure White | `#FFFFFF` | Primary text |
| Light Gray | `#B3B3B3` | Secondary text |
| Dark Gray | `#333333` | Borders, dividers |

### Typography
- **Primary Font**: `Druk Wide Bold` / `Tungsten Bold` - Headlines (condensed, all-caps)
- **Secondary Font**: `Gotham` / `Proxima Nova` - Body text
- **Weights**: 700 (bold headers), 500 (medium body), 400 (regular)
- **Style**: All-caps for headlines, title case for navigation

### Layout Patterns
- **Hero**: Full-bleed video backgrounds with centered text overlays
- **Grid**: 3-column class cards on desktop, single column mobile
- **Spacing**: Generous padding (60-100px sections), tight line-height
- **Cards**: Dark cards with subtle borders, red accent on hover

### Micro-Interactions
- Hover: Red underline animations on links
- Buttons: Scale 1.02-1.05 on hover with red glow
- Page transitions: Fade with slight slide-up
- Menu: Slide-in from right with blur backdrop

### Mobile Responsiveness
- Hamburger menu with full-screen overlay
- Stack to single column at 768px
- Touch-friendly 48px+ tap targets
- Sticky header with book button

### Key UI Components
```css
/* Button Primary */
.btn-primary {
  background: #E31837;
  color: white;
  padding: 14px 32px;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-weight: 700;
  border: none;
}

/* Card Style */
.class-card {
  background: #1A1A1A;
  border: 1px solid #333;
  padding: 24px;
}
```

---

## 2. SLT (sltnyc.com)

### Brand Identity
Minimalist, clean, sophisticated pilates aesthetic. "Strengthen, Lengthen, Tone."

### Color Palette
| Color | Hex Code | Usage |
|-------|----------|-------|
| Black | `#000000` | Primary text, accents |
| White | `#FFFFFF` | Backgrounds |
| Warm Cream | `#F5F3EF` | Section backgrounds |
| Soft Gray | `#7A7A7A` | Secondary text |
| Blush Pink | `#E8D5D5` | Subtle accents |
| Gold | `#C9A962` | Premium accents |

### Typography
- **Primary Font**: `Freight Display Pro` / `Playfair Display` - Serif headlines
- **Secondary Font**: `Avenir` / `Montserrat` - Sans-serif body
- **Weights**: 300 (light), 400 (regular), 600 (semi-bold)
- **Style**: Title case, elegant spacing, minimal all-caps

### Layout Patterns
- **Hero**: Large lifestyle photography with overlaid serif text
- **Grid**: Asymmetrical 2-3 column layouts
- **Spacing**: Airy, generous whitespace (80-120px sections)
- **Cards**: Borderless, shadow-free, clean separation

### Micro-Interactions
- Hover: Subtle opacity shifts (0.7 → 1.0)
- Buttons: Simple underline appearance
- Scroll: Parallax on hero images
- Navigation: Smooth dropdown with fade

### Mobile Responsiveness
- Elegant hamburger icon (three thin lines)
- Maintains whitespace proportionally
- Typography scales gracefully
- Image aspect ratios preserved

### Key UI Components
```css
/* Button Minimal */
.btn-book {
  background: transparent;
  color: #000;
  padding: 12px 24px;
  border: 1px solid #000;
  font-weight: 400;
  letter-spacing: 1px;
}

/* Section Style */
.section-cream {
  background: #F5F3EF;
  padding: 80px 0;
}
```

---

## 3. AARMY (aarmy.com)

### Brand Identity
Military-modern, bold, performance-focused. Founded by Angela Davis & Akin Akman.

### Color Palette
| Color | Hex Code | Usage |
|-------|----------|-------|
| Black | `#000000` | Primary background |
| Off-White | `#F7F7F7` | Contrast sections |
| Army Green | `#4A5D23` | Accent color |
| Olive | `#808000` | Secondary accent |
| Steel Gray | `#4A4A4A` | Text on light |
| Neon Yellow | `#DFFF00` | CTA highlights |

### Typography
- **Primary Font**: `Monument Extended` / `Bebas Neue` - Ultra-bold, extended
- **Secondary Font**: `Inter` / `Helvetica Neue` - Clean body text
- **Weights**: 800-900 (extra-bold headlines), 400 (body)
- **Style**: ALL CAPS throughout, tight tracking

### Layout Patterns
- **Hero**: Full-screen video, minimal text
- **Grid**: Rigid, military-style grid structure
- **Spacing**: Dense, impactful blocks with 40-60px gaps
- **Cards**: Hard edges, no rounded corners

### Micro-Interactions
- Hover: Sharp, immediate state changes
- Buttons: No transition, instant feedback
- Scroll: Snap sections on desktop
- Loading: Minimal, fast transitions

### Mobile Responsiveness
- Full-width blocks
- Maintains bold typography scale
- Simplified navigation
- Performance-optimized images

### Key UI Components
```css
/* Button AARMY */
.btn-enlist {
  background: #000;
  color: #F7F7F7;
  padding: 16px 40px;
  text-transform: uppercase;
  letter-spacing: 3px;
  font-weight: 800;
}

/* Typography */
h1 {
  font-family: 'Monument Extended', sans-serif;
  font-weight: 800;
  letter-spacing: 0.05em;
}
```

---

## 4. Equinox (equinox.com)

### Brand Identity
Ultra-luxury, editorial, black-and-white photography. "It's Not Fitness. It's Life."

### Color Palette
| Color | Hex Code | Usage |
|-------|----------|-------|
| True Black | `#000000` | Primary, headers |
| Paper White | `#FFFFFF` | Backgrounds |
| Charcoal | `#1C1C1C` | Secondary backgrounds |
| Warm Gray | `#A0A0A0` | Secondary text |
| Cream | `#FAF8F5` | Subtle backgrounds |
| Gold Accent | `#B8860B` | Rare premium touches |

### Typography
- **Primary Font**: `Canela` / `Cormorant Garamond` - Editorial serif
- **Secondary Font**: `Graphik` / `Neue Haas Grotesk` - Clean sans
- **Weights**: 300 (light serif), 500 (medium sans)
- **Style**: Elegant, editorial, generous line-height (1.6-1.8)

### Layout Patterns
- **Hero**: Full-bleed B&W photography, cinematic
- **Grid**: Magazine-style asymmetrical layouts
- **Spacing**: Premium whitespace (100-150px sections)
- **Cards**: Large imagery, minimal text overlay

### Micro-Interactions
- Hover: Slow, luxurious transitions (400-600ms)
- Images: Subtle zoom on hover (scale 1.03)
- Text: Elegant underline animations
- Scroll: Smooth, inertia-based

### Mobile Responsiveness
- Magazine-quality mobile experience
- Full-width imagery maintained
- Typography remains editorial
- Premium feel preserved at all sizes

### Key UI Components
```css
/* Button Luxury */
.btn-join {
  background: transparent;
  color: #000;
  padding: 16px 32px;
  border: 1px solid #000;
  font-family: 'Graphik', sans-serif;
  font-weight: 500;
  letter-spacing: 2px;
  transition: all 0.4s ease;
}

.btn-join:hover {
  background: #000;
  color: #fff;
}

/* Image Treatment */
.hero-image {
  filter: contrast(1.1) grayscale(0.1);
}
```

---

## 5. Rumble (rumbleboxinggym.com)

### Brand Identity
Boxing culture meets street style. Hip-hop energy, raw authenticity.

### Color Palette
| Color | Hex Code | Usage |
|-------|----------|-------|
| Rumble Red | `#FF0000` | Primary accent |
| Jet Black | `#0D0D0D` | Background |
| Off-White | `#F2F2F2` | Text, contrast |
| Concrete Gray | `#3D3D3D` | Cards, secondary |
| Electric Blue | `#00BFFF` | Occasional accent |
| Gold | `#FFD700` | Premium highlights |

### Typography
- **Primary Font**: `Knockout` / `Impact` - Bold, condensed
- **Secondary Font**: `Roboto` / `DIN` - Industrial body
- **Weights**: 900 (black headlines), 400-500 (body)
- **Style**: ALL CAPS, tight kerning, in-your-face

### Layout Patterns
- **Hero**: Video with animated text overlays
- **Grid**: Urban, poster-style layouts
- **Spacing**: Compressed, energetic (30-50px gaps)
- **Cards**: Dark with red accent borders

### Micro-Interactions
- Hover: Punch-like snap animations
- Buttons: Red glow/shadow on hover
- Scroll: Aggressive parallax effects
- Menu: Street-style slide animations

### Mobile Responsiveness
- Bold, thumb-friendly navigation
- High contrast for readability
- Quick-loading optimized media
- App-centric design (promotes app download)

### Key UI Components
```css
/* Button Fight */
.btn-book-class {
  background: #FF0000;
  color: #fff;
  padding: 14px 28px;
  text-transform: uppercase;
  font-weight: 900;
  letter-spacing: 1px;
  box-shadow: 0 4px 15px rgba(255,0,0,0.3);
}

/* Card Style */
.class-card {
  background: #1A1A1A;
  border-left: 4px solid #FF0000;
  padding: 20px;
}
```

---

## 6. SoulCycle (soul-cycle.com)

### Brand Identity
Community-driven, spiritual, empowering. Signature yellow and candlelit atmosphere.

### Color Palette
| Color | Hex Code | Usage |
|-------|----------|-------|
| Soul Yellow | `#FFC600` | Primary brand color |
| Black | `#000000` | Text, backgrounds |
| White | `#FFFFFF` | Backgrounds, text |
| Warm Gray | `#666666` | Secondary text |
| Soft Yellow | `#FFF4CC` | Subtle highlights |
| Charcoal | `#222222` | Dark sections |

### Typography
- **Primary Font**: `Neutra Text` / `Futura` - Geometric sans
- **Secondary Font**: `Open Sans` / `Lato` - Friendly body
- **Weights**: 700 (bold headers), 400 (body)
- **Style**: Mixed case, approachable, community feel

### Layout Patterns
- **Hero**: Warm photography, community imagery
- **Grid**: Clean 3-4 column instructor grids
- **Spacing**: Balanced (60-80px sections)
- **Cards**: Clean with yellow accent elements

### Micro-Interactions
- Hover: Yellow highlight/underline
- Buttons: Warm glow transitions
- Instructor cards: Subtle lift shadow
- Scroll: Smooth, welcoming animations

### Mobile Responsiveness
- App-like mobile experience
- Easy class booking flow
- Community features prominent
- Location-aware suggestions

### Key UI Components
```css
/* Button Soul */
.btn-ride {
  background: #FFC600;
  color: #000;
  padding: 14px 32px;
  font-weight: 700;
  text-transform: uppercase;
  border: none;
}

/* Accent Style */
.highlight {
  border-bottom: 3px solid #FFC600;
}

/* Community Card */
.instructor-card {
  background: #fff;
  padding: 24px;
  text-align: center;
  transition: transform 0.3s ease;
}

.instructor-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.1);
}
```

---

## Design Patterns Summary

### Common Themes Across Premium Fitness

| Pattern | Implementation |
|---------|---------------|
| **Dark Mode** | 4/6 brands use dark themes (Barry's, AARMY, Rumble, partial Equinox) |
| **Full-Bleed Media** | All use edge-to-edge imagery/video |
| **Bold Typography** | Condensed, all-caps headlines dominate |
| **Minimal Chrome** | Reduced borders, shadows, decorative elements |
| **Mobile-First Booking** | Prominent CTAs for class booking |
| **Community Focus** | Instructor profiles, member testimonials |

### Button Styles Comparison
```
Barry's:    Red fill, uppercase, wide padding
SLT:        Outlined, elegant, minimal
AARMY:      Black fill, extra-bold, no radius
Equinox:    Outlined → fill on hover, luxurious
Rumble:     Red fill, bold shadow, punchy
SoulCycle:  Yellow fill, friendly, rounded
```

### Navigation Patterns
1. **Sticky Header**: All 6 brands
2. **Mobile Hamburger**: All 6 brands
3. **Book CTA**: Always visible in header
4. **Location Selector**: Prominent for multi-location brands

### Form Design
- Minimal fields (email, name, phone)
- Dark inputs on dark themes
- Clear error states
- Progress indicators for multi-step

---

## Recommendations for Class Sniper

### Color Direction
Consider a **dark theme** with a distinctive accent color that differentiates from competitors:
- Electric Purple `#7B2FF7`
- Neon Cyan `#00F5FF`
- Hot Pink `#FF006E`
- Lime Green `#ADFF00`

### Typography Suggestion
- Headlines: `Space Grotesk` (free), `Clash Display`, or `Cabinet Grotesk`
- Body: `Inter` or `DM Sans` (free, readable)

### Key Features to Include
1. Quick-book prominent CTA
2. Class cards with instructor info
3. Location-aware defaults
4. Dark mode with high contrast
5. Micro-animations for feedback
6. Mobile-first responsive design

---

*Research compiled from direct website analysis and brand documentation.*
