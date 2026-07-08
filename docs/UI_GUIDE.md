# DBMA v1.1.0 — User Interface Guide

**David Bang Ministry Archive — Personal Knowledge Operating System Interface**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Navigation](#navigation)
4. [Pages](#pages)
5. [Design System](#design-system)
6. [Components](#components)
7. [State Management](#state-management)
8. [Customization](#customization)

---

## Overview

DBMA v1.1.0 provides a professional, modular web interface for the David Bang Ministry Archive system. The UI is built on [Streamlit](https://streamlit.io/) and follows an industrialized architecture with clear separation of concerns across theme, components, state, and pages layers.

### Key Features

- **Multi-page navigation** — Five dedicated pages for different workflows
- **Consistent design system** — Semantic color tokens, typography, and spacing
- **Reusable components** — Cards, metrics, tables, dialogs, status indicators
- **Centralized state** — Unified session state management via `StateStore`
- **Professional branding** — Custom DBMA color palette with navy/gold identity

---

## Architecture

```
ui/
├── app.py                 # Main entry point, navigation router
├── theme/                 # Design tokens (colors, typography, spacing)
│   ├── colors.py          # DBMADesignSystemColors, THEME singleton
│   ├── typography.py      # Font families, sizes, weights
│   └── spacing.py         # Spacing scale, gap system
├── components/            # Reusable presentational components
│   ├── cards.py           # metric_card, status_card, doc_card
│   ├── metrics.py         # stat_metric, stat_comparison
│   ├── tables.py          # document_table, search_results_table
│   ├── dialogs.py         # confirm_action, show_info_dialog
│   └── status.py          # progress_indicator, status_badge
├── state/                 # Session state management
│   └── store.py           # StateStore class
└── pages/                 # Page rendering modules
    ├── _base.py           # BasePage class with common utilities
    ├── dashboard.py       # System overview
    ├── library.py         # Document library and search
    ├── processing.py      # Document ingestion
    ├── research.py        # Research workspace
    └── monitor.py         # System monitoring
```

### Dependency Direction

```
pages → components → theme (tokens only)
state → streamlit.session_state
app → pages + theme
```

**Rule:** UI layer does NOT import from `core/` except for version info via `core.config`.

---

## Navigation

Navigation is managed through the sidebar in `app.py`. Users select pages via a radio widget:

| Page | Icon | Description |
|------|------|-------------|
| Dashboard | 🏠 | System overview, corpus statistics, pipeline status |
| Library | 📚 | Document search, browsing, metadata display |
| Processing | 📄 | Document ingestion configuration and execution |
| Research | 🔬 | Research workspace with query and result display |
| Monitor | 💚 | System health monitoring and resource information |

### Adding a New Page

1. Create `ui/pages/newpage.py`:

```python
"""DBMA Design System — NewPage Page."""
import streamlit as st
from ui.pages._base import BasePage
from ui.theme.colors import THEME

def render_newpage_page() -> None:
    """Render the NewPage page."""
    page = BasePage(title="NewPage", icon="🆕")
    page.render_header()
    
    # Page content here
    st.markdown("Hello, NewPage!")
    
    page.render_footer()
```

2. Register in `ui/app.py`:

```python
from ui.pages.newpage import render_newpage_page

# In _render_sidebar():
pages = {
    ...
    "NewPage": ("🆕", "New Page Description"),
}

# In _render_page_content():
page_renderers = {
    ...
    "NewPage": render_newpage_page,
}
```

---

## Pages

### Dashboard (`/Dashboard`)

Provides system-wide overview:

- **System Overview Metrics** — Document count, corpus size, last processed time, system status
- **Document Corpus Statistics** — RAW folder files, output folder files, supported formats, embedding model
- **Processing Pipeline Status** — Extraction, chunking, embedding stages
- **System Health** — Hardware resources, disk usage, memory

### Library (`/Library`)

Document management interface:

- Document search with filter controls
- Search results table with pagination
- Document detail view
- Metadata display and export

### Processing (`/Processing`)

Document ingestion workflow:

- Target directory configuration
- Output directory selection
- Chunk size and overlap parameters
- OCR toggle for PDF documents
- Ingestion execution with progress feedback

### Research (`/Research`)

Research workspace:

- Query input form
- Search result display
- Result ranking visualization
- Document snippet preview

### Monitor (`/Monitor`)

System monitoring dashboard:

- CPU/memory/disk metrics
- Vector database health
- Embedding service status
- File system state

---

## Design System

### Color Palette

The DBMA design system uses semantic color tokens:

#### Brand Colors

| Token | Value | Usage |
|-------|-------|-------|
| `BRAND_PRIMARY` | `#1B365D` | Navigation, headings |
| `BRAND_SECONDARY` | `#C8943E` | Accent, highlights |

#### Surface Colors

| Token | Value | Usage |
|-------|-------|-------|
| `BG_PAGE` | `#F7F5F0` | Page background |
| `BG_SURFACE` | `#FFFFFF` | Card/panel backgrounds |
| `BG_SIDEBAR` | `#FDFCFA` | Sidebar background |

#### Text Colors

| Token | Value | Usage |
|-------|-------|-------|
| `TEXT_PRIMARY` | `#1A1A1A` | Primary text |
| `TEXT_SECONDARY` | `#5C5C5C` | Secondary text |
| `TEXT_TERTIARY` | `#8E8E8E` | Tertiary/muted text |

#### Status Colors

| Token | Value | Usage |
|-------|-------|-------|
| `STATUS_SUCCESS` | `#2D7D5B` | Success indicators |
| `STATUS_WARNING` | `#B8860B` | Warning indicators |
| `STATUS_ERROR` | `#C62828` | Error indicators |
| `STATUS_INFO` | `#1565C0` | Info indicators |

### Using Theme Tokens

```python
from ui.theme.colors import THEME

# In component rendering:
st.markdown(f"""
    <div style="color: {THEME.TEXT_PRIMARY};">
        Primary text
    </div>
""", unsafe_allow_html=True)
```

---

## Components

### Cards

| Component | Parameters | Description |
|-----------|-----------|-------------|
| `metric_card` | title, value, icon, color | Metric display card |
| `status_card` | label, status, icon | Status badge card |
| `doc_card` | title, metadata, snippet | Document summary card |

### Metrics

| Component | Parameters | Description |
|-----------|-----------|-------------|
| `stat_metric` | label, value, unit, trend | Statistical metric display |
| `stat_comparison` | baseline, current, delta | Comparison visualization |

### Tables

| Component | Parameters | Description |
|-----------|-----------|-------------|
| `document_table` | documents, columns | Document listing table |
| `search_results_table` | results, query | Search results with highlighting |

### Dialogs

| Component | Parameters | Description |
|-----------|-----------|-------------|
| `confirm_action` | message, on_confirm | Confirmation dialog |
| `show_info_dialog` | title, content, icon | Information dialog |

### Status

| Component | Parameters | Description |
|-----------|-----------|-------------|
| `progress_indicator` | value, total, label | Progress bar with label |
| `status_badge` | status, label | Colored status badge |

---

## State Management

All session state is managed through the centralized `StateStore`:

```python
from ui.state.store import StateStore

store = StateStore()

# Set a value
store.set("processing_target", "/path/to/documents")

# Get a value with default
target = store.get("processing_target", "/default/path")

# Check existence
if store.has("processing_target"):
    ...

# Delete a key
store.delete("processing_target")
```

### Namespaced Keys

State keys are automatically namespaced by prefix:

| Prefix | Full Prefix | Usage |
|--------|------------|-------|
| `app` | `dbma_app_*` | Application state |
| `sidebar` | `dbma_sidebar_*` | Sidebar configuration |
| `processing` | `dbma_processing_*` | Processing state |
| `library` | `dbma_library_*` | Library state |
| `research` | `dbma_research_*` | Research state |
| `dashboard` | `dbma_dashboard_*` | Dashboard state |
| `monitor` | `dbma_monitor_*` | Monitor state |

---

## Customization

### Extending the Theme

Create a new theme by subclassing `DBMADesignSystemColors`:

```python
from ui.theme.colors import DBMADesignSystemColors

class MyCustomTheme(DBMADesignSystemColors):
    BRAND_PRIMARY: str = "#FF0000"  # Override as needed
    BRAND_SECONDARY: str = "#00FF00"
```

### Adding Components

Follow the existing component pattern:

```python
"""DBMA Design System — My Custom Component."""
from typing import Optional
import streamlit as st
from ui.theme.colors import THEME


def my_component(title: str, value: str) -> None:
    """Render a custom component.
    
    Parameters
    ----------
    title : str
        Component title.
    value : str
        Displayed value.
    """
    html = f"""
    <div style="padding: 16px; background: {THEME.BG_SURFACE}; 
                border: 1px solid {THEME.BORDER_LIGHT}; border-radius: 6px;">
        <div style="font-size: 12px; color: {THEME.TEXT_SECONDARY};">
            {title}
        </div>
        <div style="font-size: 24px; font-weight: 700; color: {THEME.TEXT_PRIMARY};">
            {value}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
```

---

## Running the Application

```bash
cd ~/DBMA
source ~/envs/dbma311/bin/activate
streamlit run ui/app.py
```

The application will start on `http://localhost:8501` by default.

---

*Guide generated: 2026-07-07*  
*DBMA Version: v1.1.0*  
*UI Architecture: Industrialized (Multi-page, Modular)*