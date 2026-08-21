# Approved UI mockups

## Authenticated workspace V1

- File: `authenticated-workspace-v1.png`
- Status: approved and locked on 2026-08-21
- SHA-256: `D82D85F39184459ED7B810143812AE2210D8FA30B8E9D3397A287EBDE1A99728`
- Design contract: `docs/architecture/ui-design-system.md`

This mockup defines the intended visual hierarchy and character of the signed-in
Skavan workspace: nerdy technical styling, primary navigation, group/thread
navigation, collaborative chat, user context, scoped group memory, capability
visibility, responsive mobile treatment, and four selectable themes.

Use the mockup together with the design contract. Do not extract literal content,
fake user data, permissions, or authorization behavior from the image. Backend
authorization and the written context rules remain authoritative.

When a replacement is explicitly approved, add it as a new versioned file,
update the design contract and checksum, and preserve the prior mockup in Git
history. Do not silently overwrite the approved reference.

## Login and registration V1 candidate

- File: `../prototypes/login-registration-v1.html`
- Status: interactive candidate awaiting product approval
- SHA-256: `3B90FD8ECA6115E44C7435DF82C74BE023A9292627CD85ACBCDF5F3F8C294DE8`
- Design contract: `docs/architecture/ui-design-system.md`

The prototype includes sign-in and registration states, responsive reflow,
password visibility controls, and all four locked V1 themes. It is a design
reference only: forms do not transmit data or create accounts.
