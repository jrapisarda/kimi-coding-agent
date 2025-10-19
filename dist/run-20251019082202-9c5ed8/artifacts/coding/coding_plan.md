# Coding Plan (nextjs-dashboard)

## Primary Tasks
- Initialise repository structure and configuration.
- Generate baseline code scaffolding aligning with requirements.
- Create smoke tests to validate critical paths.

## Suggested Commands
- `git init`
- `npm create next-app@latest . --use-npm --ts --app --eslint`
- `npm install @tanstack/react-table`

## Key Files / Directories
- README.md
- tests/
- app/page.tsx
- app/layout.tsx

## Model Notes
Implementation plan — nextjs-dashboard (concise)

Goal: Build a typed, testable Next.js dashboard with auth, API, DB, reusable UI components, and CI/CD based on the previously analysed requirements and generated artifacts (requirements doc, user stories, acceptance criteria, ERD, API contracts, component inventory, wireframes).

1) Tech & infra decisions (brief)
- Next.js (App Router, TypeScript)
- Tailwind CSS for styling + CSS variables
- Prisma + PostgreSQL for persistent data
- NextAuth (Auth.js) or Clerk for authentication & sessions
- TanStack Query (react-query) or SWR for data fetching / caching
- Charting: Recharts / Chart.js / ApexCharts
- Testing: Vitest + Testing Library + Playwright (E2E)
- Lint + Format: ESLint + Prettier
- CI: GitHub Actions; deploy to Vercel / Render / Docker

2) High-level milestones / key coding tasks (in priority order)
- Project bootstrap & config
  - Create Next.js app with TypeScript and app router
  - Add linting, formatting, Tailwind, CI skeleton
- Data layer and auth
  - Prisma schema, migrations, seed data
  - Implement authentication (login, signup, session)
- API & business logic
  - Implement server RPC/REST routes (app/api or /api)
  - Implement authorization checks
- Dashboard shell & routing
  - Global layout, sidebar, top nav, responsive behavior
  - Protected routes (redirect to login)
- Reusable UI components & design system
  - Form inputs, tables, cards, data widgets, modals, toasts
  - Chart components
- Pages & flows
  - Dashboard overview (widgets + charts)
  - Entity CRUD pages (list, details, create/edit)
  - Settings / user profile / admin views
- State & caching
  - Setup QueryClient, global stores (if needed)
- Tests & quality
  - Unit tests for core services/components
  - Integration tests for API handlers
  - E2E tests for key user flows
- DevOps & deployment
  - Dockerfile (optional), GitHub Actions CI, environment config
  - Vercel/Render deployment config
- Documentation & handoff
  - README, env docs, API contract (OpenAPI), component inventory

3) Recommended commands (examples using pnpm; adapt to npm/yarn)
- Bootstrap:
  - pnpm create next-app@latest my-dashboard -- --typescript --app
  - cd my-dashboard
- Install main deps:
  - pnpm add prisma @prisma/client next-auth react-query axios tailwindcss postcss autoprefixer
  - pnpm add -D eslint prettier vitest @testing-library/react @testing-library/jest-dom
- Tailwind init:
  - npx tailwindcss init -p
- Prisma init/migrate:
  - npx prisma init
  - npx prisma migrate dev --name init
  - npx prisma generate
- Run:
  - pnpm dev
  - pnpm build
  - pnpm start
- Lint/format/test:
  - pnpm lint
  - pnpm format
  - pnpm test
- Seed DB (example):
  - node prisma/seed.ts
- CI A/C:
  - git add . && git commit -m "init"
  - push to remote (triggers CI)

4) Primary files & folders to create (minimum viable set)
- root
  - package.json, pnpm-lock.yaml (or yarn.lock), next.config.js, tsconfig.json
  - .env.example, README.md, Dockerfile (optional)
  - .eslintrc.cjs, .prettierrc, .github/workflows/ci.yml
- app/ (Next.js App Router)
  - app/layout.tsx (global layout + providers)
  - app/page.tsx (marketing / landing or redirect to dashboard)
  - app/dashboard/layout.tsx (dashboard shell with sidebar)
  - app/dashboard/page.tsx (dashboard overview)
  - app/(auth)/login/page.tsx, app/(auth)/signup/page.tsx
  - app/api/… route handlers (if using app router API routes)
- src/
  - components/
    - NavBar.tsx, Sidebar.tsx, Pagination.tsx, DataTable.tsx
    - Card.tsx, MetricWidget.tsx, Chart.tsx, Modal.tsx, Form.tsx
  - lib/
    - prisma.ts (Prisma client wrapper)
    - auth.ts (NextAuth config)
    - api.ts (axios/ fetch wrapper)
    - validators/ (zod schemas)
  - hooks/
    - useUser.ts, useAuthRedirect.ts, useQueryHooks.ts
  - services/
    - users.service.ts, metrics.service.ts, widgets.service.ts
  - styles/
    - globals.css (Tailwind imports), variables.css
  - prisma/
    - schema.prisma, seed.ts
- tests/
  - unit/, integration/, e2e/
- config/
  - tailwind.config.js, postcss.config.js
- infra/
  - docker-compose.yml (Postgres for dev), terraform/optional
- monitoring/docs
  - openapi.yaml (API contract), ERD.png, requirements.md, component-inventory.md

5) API / DB artifacts to produce
- prisma/schema.prisma + migrations
- seed data script
- openapi.yaml or lightweight API spec for all endpoints used by front-end
- authorization matrix (which roles can call which endpoints)
- sample Postman collection (optional)

6) Minimal development workflow (day-1 checklist)
- Initialize project + install dependencies
- Configure Tailwind + global styles
- Setup Prisma + local Postgres + run initial migration + seed
- Implement NextAuth + login page + protected redirect
- Create dashboard layout + sample widget + fetch data from API
- Add tests for auth and one API route
- Add CI skeleton and .env.example

7) Estimates & priorities (suggested)
- Day 0.5: bootstrap, repo, lint/format
- Day 1: Prisma schema + auth + seed
- Day 2: Dashboard shell + routes + a couple widgets
- Day 3–4: CRUD pages, charts, components
- Day 5: Tests, CI, docs, deploy

If you want, I can:
- Output a ready-to-run shell command sequence for initial bootstrap
- Generate the initial project file tree and starter files (layout, auth config, prisma schema)
- Produce an OpenAPI API spec draft or ERD from the earlier artifacts

Which next step would you like?
