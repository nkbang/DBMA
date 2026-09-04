---
name: Theological Archive System
colors:
  surface: '#fbf9f4'
  surface-dim: '#dbdad5'
  surface-bright: '#fbf9f4'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3ee'
  surface-container: '#f0eee9'
  surface-container-high: '#eae8e3'
  surface-container-highest: '#e4e2dd'
  on-surface: '#1b1c19'
  on-surface-variant: '#434848'
  inverse-surface: '#30312e'
  inverse-on-surface: '#f2f1ec'
  outline: '#737878'
  outline-variant: '#c3c7c7'
  surface-tint: '#596060'
  primary: '#171e1e'
  on-primary: '#ffffff'
  primary-container: '#2c3333'
  on-primary-container: '#949b9b'
  inverse-primary: '#c1c8c7'
  secondary: '#6a5c4c'
  on-secondary: '#ffffff'
  secondary-container: '#f0dcc8'
  on-secondary-container: '#6f6050'
  tertiary: '#00202d'
  on-tertiary: '#ffffff'
  tertiary-container: '#0c3647'
  on-tertiary-container: '#7b9fb3'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dde4e3'
  primary-fixed-dim: '#c1c8c7'
  on-primary-fixed: '#161d1d'
  on-primary-fixed-variant: '#414848'
  secondary-fixed: '#f3dfcb'
  secondary-fixed-dim: '#d6c3b0'
  on-secondary-fixed: '#241a0d'
  on-secondary-fixed-variant: '#514535'
  tertiary-fixed: '#c2e8fe'
  tertiary-fixed-dim: '#a7cce1'
  on-tertiary-fixed: '#001e2b'
  on-tertiary-fixed-variant: '#264b5d'
  background: '#fbf9f4'
  on-background: '#1b1c19'
  surface-variant: '#e4e2dd'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 52px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  title-lg:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-reading-lg:
    fontFamily: Source Serif 4
    fontSize: 19px
    fontWeight: '400'
    lineHeight: 32px
  body-reading-md:
    fontFamily: Source Serif 4
    fontSize: 17px
    fontWeight: '400'
    lineHeight: 28px
  label-ui:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  caption:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  sidebar-width: 280px
  reading-column: 720px
  gutter: 32px
  margin-page: 48px
---

## Brand & Style

The design system is crafted for a scholarly environment, embodying the quiet focus of a theological research desk. The target audience includes theologians, pastors, and students who engage in deep study. The emotional response is one of **reverence, calm, and intellectual clarity**.

The style is **Minimalism with a Tactile focus**, prioritizing high-quality typography and a "paper-like" digital experience. We avoid all modern "tech" tropes like vibrant gradients, glassmorphism, or heavy shadows. Instead, we use subtle tonal shifts and precise grid alignment to create a structured, professional workspace that feels as reliable as a leather-bound volume.

## Colors

The palette is designed to minimize eye strain during multi-hour research sessions.

- **Primary (Deep Charcoal):** Used for primary text and core UI frameworks to provide a solid, authoritative grounding.
- **Background (Soft Cream):** The base layer for all "Original Source" materials, mimicking premium archival paper.
- **Secondary (Muted Wood):** Used for navigation headers and organizational categories to provide a warm, human touch.
- **Accents (Scholar Blue):** A conservative blue reserved strictly for primary calls to action and active states.
- **AI Distinction:** AI-generated summaries and insights are placed on a subtle cool-grey surface (`#F0F4F8`) to clearly differentiate synthesized data from primary historical sources.

## Typography

The system employs a dual-typeface strategy to balance functional UI and immersive reading.

- **UI Elements:** Use **Hanken Grotesk** for navigation, labels, and headers. It is clean, contemporary, and maintains professional neutrality. 
- **Reading Content:** Use **Source Serif 4** for all primary theological texts. This serif is specifically optimized for long-form legibility and carries a traditional, scholarly weight.
- **Hierarchy:** We use a generous line-height (1.6x - 1.7x) for body text to allow the eye to travel easily across dense theological arguments. 
- **Korean Localization:** All headings and UI labels use pastoral terminology (e.g., '서지 정보', '말씀 묵상', '자료 보관함').

## Layout & Spacing

The layout is a **Fixed-Fluid Hybrid** model centered around the reading experience.

1.  **Sidebar (Left):** A fixed 280px navigation area for archive categories and search.
2.  **Research Canvas (Center):** A fluid area that contains the document viewer. The reading column itself is capped at **720px** to maintain an ideal line length for high-speed comprehension.
3.  **Utility Panel (Right):** An optional collapsible panel for AI insights and cross-references.

We use a **8px grid system**. Spacing between blocks of text and UI components is intentionally large to prevent visual clutter and promote a sense of "mental room."

## Elevation & Depth

This design system rejects deep shadows in favor of **Tonal Layering and Fine Outlines**.

- **Level 0 (Base):** The main application background (Warm Cream).
- **Level 1 (Raised):** Document cards or AI insight boxes. These are defined by a 1px solid border (`#E5E1D8`) rather than a shadow.
- **Level 2 (Interaction):** Hover states use a very subtle, low-blur "Scholar Tint" (a faint blue or tan glow) to indicate interactivity without breaking the flat, paper-like aesthetic.
- **Separators:** Use thin, 1px horizontal rules in a muted secondary color to divide sections of text.

## Shapes

The shape language is **Soft and Traditional**. 

We use a very subtle corner radius (4px - 8px) to soften the UI without making it feel "bubbly" or informal. Buttons and input fields should feel like physical stationery. Large containers, such as the document viewer, may remain sharp (0px) to maximize the "document" feel, while smaller UI components like chips for keywords use the soft radius.

## Components

- **Primary Action (주요 작업):** Buttons are solid 'Scholar Blue' with white Hanken Grotesk text. No gradients.
- **Secondary Action (부차적 작업):** Ghost buttons with a thin charcoal border.
- **Theological Cards (자료 카드):** Used for search results. They feature a Source Serif title, a short Hanken Grotesk snippet, and a 'Date/Source' label in the footer.
- **Document Viewer (연구 공간):** A clean, distraction-free white/cream sheet. Navigation is hidden until the user moves the mouse to the top edge.
- **Search Bar (자료 찾기):** Large, centered, and simple. It uses a serif font for the input text to match the feeling of typing a manuscript.
- **AI Insights (연구 도우미):** These components always use the `ai_surface_hex` background and a distinct icon to signify synthesized content.