# Agents.md — KaziX

## 🤖 AI Agent Instructions

### Context
You are working on **KaziX**, a Kenyan marketplace for skilled workers (fundis). The platform aims to bridge the gap between clients and pros using technology and trust.

### Design & Aesthetic
- **Modern Brutalist:** High-contrast, bold, and clear. Avoid over-complicated gradients or animations.
- **Typography:**
  - `Syne`: Used for all high-impact headings and branding.
  - `DM Sans`: Used for body text and readability.
- **Color Palette:**
  - Ink (`#0D0D0D`): Main text and dark elements.
  - Cream (`#F5F0E8`): Background and contrast.
  - Saffron (`#F5A623`): Primary accent, branding.
  - Rust (`#C0392B`): Urgency and errors.
  - Green (`#1B6B3A`): Success and confirmations.

### Local Context (Kenya)
- **M-Pesa First:** All payment logic must be designed around M-Pesa (STK push, escrow, C2B/B2C).
- **Mobile-First:** A large percentage of users will be on mobile devices. Ensure all frontend changes are responsive and performant.
- **SMS Alerts:** Notifications are primarily SMS-driven for workers.

### Technical Constraints
- **Frontend:** Stick to **Vanilla CSS3** and **modern HTML5**. Avoid introducing heavy frontend frameworks (e.g., React, Vue).
- **Backend:** FastAPI environment.

## 📌 Versioning
- This project follows [Semantic Versioning (SemVer)](https://semver.org/).
- Current Version: `0.1.0-alpha`

## 🪝 Git Hooks
- **Pre-commit:** Ensure `ruff` is run for backend linting and `pytest` for backend testing.
- **Pre-push:** All tests must pass before pushing to the main branch.

## 💡 Best Practices
- **Security:** Prioritize ID verification and escrow logic.
- **Trust:** Emphasize review systems and verified profiles.
- **Accessibility:** Ensure high contrast and readable text for all users.
