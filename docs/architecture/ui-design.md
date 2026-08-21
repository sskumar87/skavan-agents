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
