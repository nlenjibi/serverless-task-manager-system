# Serverless Task Manager

Event-driven task management app built with **AWS SAM**: Cognito auth, API
Gateway + Lambda + DynamoDB for CRUD, and EventBridge Scheduler + DynamoDB
Streams + SQS FIFO for expiry/cancellation. The `frontend/` folder is a
Next.js app hosted on AWS Amplify as a monorepo build, optionally provisioned
by this stack.

## Architecture

```
User → Amplify (Next.js app) → API Gateway (Cognito authorizer) → Lambda → DynamoDB
                                                                       ↓
                                                     EventBridge Scheduler (per-task deadline)
                                                                       ↓
                                                     TaskExpiryLambda → SNS email
                                                                       ↑
DynamoDB Streams → StreamProcessor → SQS FIFO (+ DLQ) → CancellationHandler
                                                              ↓
                                                   Delete Scheduler rule
```

See `docs/architecture.md` for detailed Mermaid diagrams of each flow.

## AWS Services

| Service | Role |
|---|---|
| **Cognito User Pool** | Authentication (PreSignUp auto-confirms, PostAuth subscribes email to SNS) |
| **API Gateway** | REST API with Cognito authorizer, access logging + metrics to CloudWatch |
| **Lambda (×9)** | CRUD, auth triggers, expiry, stream processor, cancellation — structured logging + X-Ray tracing via AWS Lambda Powertools |
| **DynamoDB** | Task storage (`UserId`/`TaskId` key), Streams, point-in-time recovery |
| **EventBridge Scheduler** | Per-task one-time schedule fires at deadline |
| **SNS** | Email notification to task owner on expiry |
| **SQS FIFO + DLQ** | Decoupled cancellation queue (DynamoDB Streams → SQS → Lambda), poison messages routed to a dead-letter queue |
| **Amplify Hosting** | Hosts `frontend/` as a monorepo build (optional — only provisioned when `FrontendRepoUrl` is set) |

## DynamoDB Schema

| Attribute | Type | Description |
|---|---|---|
| `UserId` (PK) | String | Cognito `sub` |
| `TaskId` (SK) | String | UUID |
| `Description` | String | Task description |
| `Date` | String | Task date (`YYYY-MM-DD`) |
| `Status` | String | `Pending` / `Completed` / `Expired` |
| `Deadline` | String | ISO-8601 — defaults to 5 min after creation, optionally overridden on create |
| `CreatedAt` / `UpdatedAt` | String | ISO-8601 |
| `UserEmail` | String | Owner email (denormalised) |

## Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed
- Python 3.12
- Node.js 18+ (frontend only)

## Deploy the backend

```bash
sam build --parallel
sam deploy --guided   # first time
sam deploy            # subsequent deploys
```

Copy the stack **Outputs** (`ApiUrl`, `UserPoolId`, `UserPoolClientId`) into
`frontend/.env.local`.

## Frontend

`frontend/` is a Next.js 14 + TypeScript app (`aws-amplify` for Cognito auth,
Axios for API calls), built as part of this same repo. It expects:

| Env var | Value |
|---|---|
| `NEXT_PUBLIC_USER_POOL_ID` | This stack's `UserPoolId` output |
| `NEXT_PUBLIC_USER_POOL_CLIENT_ID` | This stack's `UserPoolClientId` output |
| `NEXT_PUBLIC_API_URL` | This stack's `ApiUrl` output |
| `NEXT_PUBLIC_AWS_REGION` | The deploy region |

```bash
cd frontend
cp .env.local.example .env.local   # fill in the values above
npm install
npm run dev                         # local dev server on :3000
# or
npm test                            # Jest unit tests
npm run build                       # production build, same as Amplify runs
```

### Hosting the frontend on Amplify

Two options:

**A. Let this template provision Amplify Hosting** — create a GitHub personal
access token with `repo` scope for *this* repo, then:

```bash
sam deploy --parameter-overrides \
  Stage=dev \
  FrontendRepoUrl=https://github.com/<you>/serverless-task-manager-system \
  FrontendRepoBranch=main \
  GitHubAccessToken=<token>
```

This creates `AWS::Amplify::App`/`Branch` with a monorepo `BuildSpec`
(`appRoot: frontend`), wires the four `NEXT_PUBLIC_*` env vars from this
stack's own outputs, and rebuilds on every push to that branch. The app URL
is printed as the `AmplifyDefaultDomain` stack output.

**B. Connect the repo manually in the Amplify console** — leave
`FrontendRepoUrl` blank, connect this repo, enable "Monorepo" and set the app
root to `frontend`, and paste the four `NEXT_PUBLIC_*` values into the
Amplify app's environment variables yourself.

## CI/CD

`.github/workflows/deploy.yml` lints and validates on every push/PR to
`main` (`flake8` over `src/`, `sam validate --lint`). Actual deployment to AWS
is handled outside GitHub Actions, via AWS CodePipeline's Git Sync
integration against this repo — see the `aws-sync-main-*` branches.

## Lambda Functions

| Function | Trigger | Description |
|---|---|---|
| `PreSignUp` | Cognito PreSignUp | Auto-confirms users |
| `PostAuth` | Cognito PostAuthentication | Subscribes email to SNS |
| `CreateTask` | POST /tasks | Creates task + EventBridge schedule (deadline optional, defaults to +5 min) |
| `GetTasks` | GET /tasks | Lists all user tasks (returns a bare JSON array) |
| `UpdateTask` | PUT /tasks/{id} | Updates task |
| `DeleteTask` | DELETE /tasks/{id} | Deletes task |
| `TaskExpiry` | EventBridge Scheduler | Marks task Expired + sends SNS |
| `StreamProcessor` | DynamoDB Streams | Routes cancellation events to SQS FIFO |
| `CancellationHandler` | SQS FIFO | Deletes EventBridge schedule |

All handlers share `src/lib/ddb.py` (table handle), `src/lib/http.py`
(response envelope, CORS, Cognito claim extraction), and
`src/lib/observability.py` (Powertools `Logger`/`Tracer`).
