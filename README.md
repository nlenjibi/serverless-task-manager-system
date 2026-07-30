# Serverless Task Manager

Event-driven task management **backend** built with **AWS SAM**: Cognito
auth, API Gateway + Lambda + DynamoDB for CRUD, and EventBridge Scheduler +
DynamoDB Streams + SQS FIFO for expiry/cancellation. The frontend
(`serverless-task-manager-frontend`, a Next.js app) lives in its own sibling
repo and is not provisioned by this template — host it however you like
(e.g. connect it to Amplify manually in the console).

## Architecture

```
User → Frontend (Next.js app) → API Gateway (Cognito authorizer) → Lambda → DynamoDB
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
the frontend's `.env.local` (see the `serverless-task-manager-frontend` repo).

## Frontend

The frontend lives in the sibling **`serverless-task-manager-frontend`**
repo — a Next.js 14 + TypeScript app (`aws-amplify` for Cognito auth, Axios
for API calls). It expects:

| Env var | Value |
|---|---|
| `NEXT_PUBLIC_USER_POOL_ID` | This stack's `UserPoolId` output |
| `NEXT_PUBLIC_USER_POOL_CLIENT_ID` | This stack's `UserPoolClientId` output |
| `NEXT_PUBLIC_API_URL` | This stack's `ApiUrl` output |
| `NEXT_PUBLIC_AWS_REGION` | The deploy region |

See that repo's own README for local dev (`npm run dev`) and test
(`npm test`) instructions, and its `amplify.yml` if you want to host it on
AWS Amplify (connect it manually in the console — this template doesn't
provision Amplify hosting).

## CI/CD

`.github/workflows/pipeline.yaml` is the GitHub Actions pipeline (generated
via `sam pipeline init`/`bootstrap`) that tests and deploys this stack.

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
