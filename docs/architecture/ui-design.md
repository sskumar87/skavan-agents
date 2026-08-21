# UI design and saved appearance preferences

## Visual direction

The normal-user web app uses a command-centre workspace: a dark or light application shell, slim navigation, crisp status indicators, structured panels and restrained accent colour. It must remain comfortable for extended collaborative chat use rather than mimic the Hermes operator dashboard.

The application is responsive by default:

- **Desktop:** persistent navigation plus the current workspace.
- **Tablet:** compact/collapsible navigation and full conversation workspace.
- **Mobile:** single-pane workspace with navigation in a drawer or sheet; controls remain touch-friendly.

## Theme preference

Appearance is a per-user product preference. The user can choose one of four named theme families in **Profile / Settings → Appearance**:

1. Midnight cyan
2. Ember
3. Violet signal
4. Copper slate

Each family includes a dark and daylight mode. The settings UI shows a preview of both modes before selection.

The selected family and mode are stored against the canonical platform user record—not in browser-only storage. On future sign-in, the backend returns the saved preference and the web app applies it before rendering the workspace. The selected appearance remains active across devices and sessions until the user changes it.

Until a preference is saved, the default is **Midnight cyan / dark**. A system-following mode may be considered later, but is not required for V1.

## Data and API contract

The identity/settings slice adds a `user_preferences` record keyed by `user_id`, with a unique row per user. Initial fields:

| Field | Values |
| --- | --- |
| `theme_family` | `midnight_cyan`, `ember`, `violet_signal`, `copper_slate` |
| `color_mode` | `dark`, `light` |
| `updated_at` | timestamp |

The authenticated user endpoint returns these fields. An authenticated update endpoint validates the enumerated values and persists the change. Theme preference is personal data only: group roles and group membership never affect it.

## Component consistency

All screens use the same app shell and theme tokens. The first component set includes navigation, buttons, form controls, chat messages, approval cards, status indicators, empty/loading/error states, group/thread lists and settings controls. Components must retain keyboard access, visible focus states and usable contrast in every supported theme.

## UI development standard

This is the mandatory baseline for all normal-user UI work. New screens and features must extend the shared system rather than introduce one-off visual treatments.

### Generic design system

- Build from reusable primitives and product components, not page-specific markup.
- Use semantic design tokens for every colour, surface, border, text treatment, spacing, radius, shadow and focus state. Components consume tokens; they do not hard-code a theme colour.
- A component has one shared structure across themes. Theme selection changes token values only, never information architecture, authorization behaviour or user flows.
- Add a component to the shared library when the same pattern appears twice. Do not duplicate chat bubbles, cards, navigation items, dialogs, forms or status indicators across pages.
- Keep normal-user product UI distinct from the Hermes operator dashboard.

### Responsive and accessible by default

- Design mobile-first, then adapt for tablet and desktop.
- Support a 320px-wide mobile viewport, tablet layouts and desktop layouts without clipped controls or horizontal scrolling.
- Use touch targets of at least 44 × 44 CSS pixels where controls are primarily touch-operated.
- Use semantic HTML, keyboard operation, visible focus indicators and accessible labels. Do not use colour as the only way to communicate state.
- Verify readable contrast in all four theme families and both colour modes.

### Delivery gate for UI changes

Every UI pull request must:

1. Reuse existing tokens and components, or explicitly add a documented shared component.
2. Show the selected appearance preference working in dark and daylight mode.
3. Verify desktop, tablet and mobile layouts for the changed flow.
4. Include keyboard and focus-state verification for new interactive elements.
5. Avoid browser-only persistence for product settings; user preferences are read from and written to the authenticated backend API.

Changes that need a new visual direction, token family or navigation model must update this document before implementation.
