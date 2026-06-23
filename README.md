# Serverless Todo App — Backend

Event-driven task management backend built with **AWS SAM**.

## Architecture

```
User → API Gateway (Cognito auth) → Lambda → DynamoDB
                                            ↓
                               EventBridge Scheduler (per-task deadline)
                                            ↓
                               TaskExpiryLambda → SNS email
                                            ↑
DynamoDB Streams → StreamProcessor → SQS FIFO → CancellationHandler
                                                      ↓
                                           Delete Scheduler rule
```

## AWS Services

| Service | Role |
|---|---|
| **Cognito User Pool** | Authentication (PreSignUp auto-confirms, PostAuth subscribes email to SNS) |
| **API Gateway** | REST API with Cognito authorizer |
| **Lambda (×7)** | CRUD, auth triggers, expiry, stream processor, cancellation |
| **DynamoDB** | Single-table task storage with Streams |
| **EventBridge Scheduler** | Per-task one-time schedule fires at deadline |
| **SNS** | Email notification to task owner on expiry |
| **SQS FIFO** | Decoupled cancellation queue (DynamoDB Streams → SQS → Lambda) |

## DynamoDB Schema

| Attribute | Type | Description |
|---|---|---|
| `UserId` (PK) | String | Cognito `sub` |
| `TaskId` (SK) | String | UUID |
| `Description` | String | Task description |
| `Date` | String | Task date (`YYYY-MM-DD`) |
| `Status` | String | `Pending` / `Completed` / `Expired` |
| `Deadline` | String | ISO-8601 — 5 min after creation |
| `CreatedAt` | String | ISO-8601 |
| `UpdatedAt` | String | ISO-8601 |

## Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed
- Python 3.12

## Deploy

```bash
sam build --parallel
sam deploy --guided   # first time
sam deploy            # subsequent deploys
```

Copy the **Outputs** (ApiUrl, UserPoolId, UserPoolClientId) into the frontend `.env.local`.

## CI/CD

GitHub Actions pipeline (`.github/workflows/deploy.yml`) runs on every push to `main`:

1. Lint Lambda code with `flake8`
2. Validate SAM template
3. `sam build --cached --parallel`
4. `sam deploy --no-confirm-changeset`

### Required GitHub Secrets

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |

## Lambda Functions

| Function | Trigger | Description |
|---|---|---|
| `PreSignUp` | Cognito PreSignUp | Auto-confirms users |
| `PostAuth` | Cognito PostAuthentication | Subscribes email to SNS |
| `CreateTask` | POST /tasks | Creates task + EventBridge schedule |
| `GetTasks` | GET /tasks | Lists all user tasks |
| `UpdateTask` | PUT /tasks/{id} | Updates task |
| `DeleteTask` | DELETE /tasks/{id} | Deletes task |
| `TaskExpiry` | EventBridge Scheduler | Marks task Expired + sends SNS |
| `StreamProcessor` | DynamoDB Streams | Routes cancellation events to SQS FIFO |
| `CancellationHandler` | SQS FIFO | Deletes EventBridge schedule |
