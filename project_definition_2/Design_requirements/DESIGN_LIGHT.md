# Design System: Editorial Engineering (Light Mode)

## 1. Overview & Creative North Star: "The Technical Curator"
This design system moves beyond the standard SaaS dashboard to embrace an **Editorial Engineering** aesthetic. The "Creative North Star" is **The Technical Curator**—a visual language that treats data metrics with the same reverence and clarity as a high-end architectural journal. 

The system rejects the "box-within-a-box" monotony of traditional UI. Instead, it utilizes **intentional asymmetry**, expansive white space, and **tonal layering** to create a sense of focused authority. By removing structural lines and relying on background shifts, we create a fluid, premium environment that feels engineered yet human.

---

### 2. Colors: Tonal Architecture
The palette is rooted in a sophisticated range of whites and cool grays, punctuated by a deep, intellectual Indigo.

#### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to section content. Boundaries must be defined solely through background color shifts. For example, a `surface-container-low` section sitting on a `surface` background provides all the definition needed.

#### Surface Hierarchy & Nesting
Depth is achieved through "Tonal Stacking." Rather than flat grids, treat the UI as physical layers of fine paper:
- **Base Layer:** `surface` (#f8f9fa)
- **Primary Content Areas:** `surface-container-lowest` (#ffffff)
- **Nested Controls/Sidebars:** `surface-container` (#edeeef) or `surface-container-high` (#e7e8e9)

#### Signature Textures & Glass
- **The Indigo Pulse:** Use a subtle gradient from `primary` (#4648d4) to `primary_container` (#6063ee) for hero CTAs to add a "liquid" professional polish.
- **Glassmorphism:** For floating menus or navigation overlays, use `surface_container_lowest` at 80% opacity with a `24px` backdrop-blur.

---

### 3. Typography: Space & Structure
The typography system uses **Space Grotesk** for technical precision and **Inter** for legible data consumption.

- **Display & Headlines (Space Grotesk):** These are your "Editorial Anchors." Use `display-lg` and `headline-md` with tight letter-spacing (-0.02em) to create a bold, "magazine-header" feel. 
- **The Metadata Balance (Inter):** All body copy and data points use Inter. The contrast between the geometric, quirky Space Grotesk and the neutral Inter signals the shift between "Human Narrative" and "Hard Data."
- **Labeling:** `label-sm` (Space Grotesk) should always be uppercase with +0.05em tracking when used for category headers or DORA performance badges.

---

### 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are largely replaced by light-source simulation and surface shifts.

- **The Layering Principle:** To highlight a metric card, do not add a border. Place a `surface-container-lowest` (#ffffff) card atop a `surface-container-low` (#f3f4f5) background. The delta in brightness creates a "Soft Lift."
- **Ambient Shadows:** If a card must "float" (e.g., a modal or active state), use a shadow with a 40px blur, 0% spread, and 4% opacity, using the `on-surface` color (#191c1d) as the shadow tint.
- **The "Ghost Border" Fallback:** If accessibility requirements demand a border, use `outline-variant` at **15% opacity**. High-contrast, 100% opaque borders are strictly forbidden.

---

### 5. Components: The Editorial Set

#### Performance Badges (DORA Specific)
Badges must prioritize legibility without breaking the "Editorial" palette.
- **ELITE:** `primary` background with `on_primary` text. (High-contrast Indigo).
- **HIGH:** `secondary_container` background with `on_secondary_container` text.
- **MEDIUM:** `tertiary_fixed` background with `on_tertiary_fixed_variant` text.
- **LOW:** `error_container` background with `on_error_container` text.
*Note: Use `md` (0.375rem) corner radius for badges to maintain a modern, technical "chip" look.*

#### Buttons
- **Primary:** Gradient fill (`primary` to `primary_container`). `xl` (0.75rem) radius. White text.
- **Secondary:** `surface_container_high` background. No border. Space Grotesk `label-md` weight.
- **Tertiary/Ghost:** No background. Underline on hover only.

#### Cards & Data Lists
- **Rule:** Forbid divider lines.
- **Implementation:** Separate list items using `1.5` (0.5rem) or `2` (0.7rem) spacing units. Use a subtle `surface_variant` hover state to define the row interaction.
- **Asymmetric Layouts:** In a card, place the metric value (e.g., "4.2 Days") in `display-sm` at the top left, and the label ("Cycle Time") in `label-sm` at the bottom right. This intentional "editorial" placement breaks the standard centered-grid fatigue.

#### Input Fields
- Use `surface_container_low` as the field background. 
- **Focus State:** Transition the background to `surface_container_lowest` and add a 1px `primary` (Indigo) bottom-border only. This mimics a "signature line" on a document.

---

### 6. Do's and Don'ts

#### Do
- **Do** use `20` (7rem) and `24` (8.5rem) spacing scales to create "Breathable Voids" between major data sections.
- **Do** use Indigo (`primary`) sparingly as a precise "laser" to guide the eye to the most important metric.
- **Do** use `Space Grotesk` for all numbers to lean into the technical, monospaced-adjacent aesthetic.

#### Don't
- **Don't** use 1px gray borders. Ever.
- **Don't** use pure black (#000000) for text. Use `on_surface` (#191c1d) to maintain the soft, premium feel of ink on paper.
- **Don't** crowd the interface. If a screen feels "busy," increase the background tonal contrast and double the vertical padding.