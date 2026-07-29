# Serverless Todo App — Frontend

Next.js 14 + TypeScript frontend for the serverless todo application, hosted on **AWS Amplify**.

> This folder lives inside the `serverless-task-manager-system` repo (monorepo) —
> see `../template.yaml` and the root `README.md` for how the backend
> provisions Amplify Hosting for it.

## Tech Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **aws-amplify v6** (Cognito authentication)
- **Axios** (API calls to API Gateway)
- **Zustand** (auth state)

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── (auth)/login/       # Login page
│   ├── (auth)/register/    # Register page
│   └── dashboard/          # Main task dashboard (protected)
├── features/
│   ├── auth/               # Login, Register, hooks, Cognito service
│   └── tasks/              # Task list, card, modal, hooks, API service
├── components/layout/      # Navbar
├── lib/                    # api.ts (axios), amplify-config.ts, utils, constants
├── store/                  # Zustand auth store
└── types/                  # Shared TypeScript types
test/                       # Jest unit tests
```

## Local Development

```bash
cd frontend
cp .env.local.example .env.local
# Fill in values from the backend stack Outputs (see root README.md)

npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_AWS_REGION` | AWS region (e.g. `us-east-1`) |
| `NEXT_PUBLIC_USER_POOL_ID` | Cognito User Pool ID |
| `NEXT_PUBLIC_USER_POOL_CLIENT_ID` | Cognito App Client ID |
| `NEXT_PUBLIC_API_URL` | API Gateway base URL |

Set these in **Amplify Console → App settings → Environment variables** for hosted builds.

## Amplify Hosting

This app is built as part of a monorepo — the app root is `frontend/`, not
the repo root. Two ways to host it:

1. **Via the backend's `template.yaml`** (recommended) — `sam deploy
   --parameter-overrides FrontendRepoUrl=<this repo's URL> ...` provisions
   `AWS::Amplify::App`/`Branch` with a monorepo `BuildSpec` (`appRoot:
   frontend`) and wires the four `NEXT_PUBLIC_*` env vars automatically from
   the backend stack's outputs.
2. **Manually in the Amplify console** — connect this repository, enable
   "Monorepo" and set the app root to `frontend`, then set the four
   `NEXT_PUBLIC_*` environment variables yourself (this folder's
   `amplify.yml` is used as the build spec once the app root is set).

Every push to the configured branch triggers an automatic redeploy either way.

## Tests

```bash
npm test
```
