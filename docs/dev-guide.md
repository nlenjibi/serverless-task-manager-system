# Developer Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Local Setup](#local-setup)
4. [Lambda Functions Reference](#lambda-functions-reference)
5. [Event-Driven Workflows](#event-driven-workflows)
6. [Deploy to AWS](#deploy-to-aws)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Environment Variables](#environment-variables)
9. [Observability](#observability)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| AWS CLI | v2 | `winget install Amazon.AWSCLI` |
| AWS SAM CLI | v1.115 | `winget install Amazon.SAM-CLI` |
| Python | 3.12 | `winget install Python.Python.3.12` |
| Docker | any | Required for `sam build` (Lambda container) |
| Node.js | 18 | For frontend only |

Configure AWS credentials before local development:

```bash
aws configure
# or use SSO: aws configure sso
```

---

## Project Structure

```
serverless-task-manager-system/
│
├── template.yaml                  # SAM / CloudFormation — all infrastructure
├── samconfig.toml                 # SAM deploy defaults (region, stack name, etc.)
│
├── lambdas/
│   ├── pre_signup/                # Cognito PreSignUp trigger
│   │   └── handler.py
│   ├── post_auth/                 # Cognito PostAuthentication trigger
│   │   └── handler.py
│   ├── create_task/               # POST /tasks
│   │   └── handler.py
│   ├── get_tasks/                 # GET /tasks
│   │   └── handler.py
│   ├── update_task/               # PUT /tasks/{taskId}
│   │   └── handler.py
│   ├── delete_task/               # DELETE /tasks/{taskId}
│   │   └── handler.py
│   ├── task_expiry/               # EventBridge Scheduler → mark Expired + SNS
│   │   └── handler.py
│   ├── stream_processor/          # DynamoDB Streams → SQS FIFO
│   │   └── handler.py
│   └── cancellation_handler/      # SQS FIFO → delete EventBridge schedule
│       └── handler.py
│
├── docs/
│   ├── dev-guide.md               # This file
│   └── architecture.md            # Mermaid architecture diagrams
│
└── .github/
    └── workflows/
        └── deploy.yml             # GitHub Actions CI/CD (OIDC auth)
```

---

## Local Setup

### 1. Clone and install SAM CLI

```bash
git clone https://github.com/nlenjibi/serverless-task-manager-system.git
cd serverless-task-manager-system
```

### 2. Build the Lambda functions

```bash
sam build --parallel
```

SAM packages each Lambda function's dependencies into `.aws-sam/build/`.

### 3. Run the API locally

```bash
sam local start-api --warm-containers EAGER
```

The API will be available at `http://localhost:3000`. Note: Cognito authorizer is **skipped** locally — pass any `Authorization` header with a JSON payload matching the Cognito claims shape when testing with `curl` or Postman:

```bash
# Example: create a task locally (auth is bypassed in local SAM)
curl -X POST http://localhost:3000/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Buy groceries", "date": "2025-01-15"}'
```

### 4. Invoke a single function locally

```bash
# Invoke task expiry handler with a test event
sam local invoke TaskExpiryFunction \
  --event events/task-expiry-event.json
```

Create test events in `events/` as needed:

```json
// events/task-expiry-event.json
{
  "taskId": "test-task-123",
  "userId": "test-user-456"
}
```

---

## Lambda Functions Reference

### PreSignUpFunction

**Trigger:** Cognito PreSignUp  
**Purpose:** Auto-confirms every new user registration so no email verification step is required.

```python
event['response']['autoConfirmUser'] = True
event['response']['autoVerifyEmail'] = True
```

**IAM permissions:** None (Cognito invokes it directly).

---

### PostAuthFunction

**Trigger:** Cognito PostAuthentication  
**Purpose:** Subscribes the user's email to the SNS topic with a **filter policy** keyed on `userId`. This ensures each user only receives notifications for their own tasks.

```python
sns.subscribe(
    TopicArn=SNS_TOPIC_ARN,
    Protocol='email',
    Endpoint=email,
    Attributes={'FilterPolicy': json.dumps({"userId": [user_id]})}
)
```

> The subscription requires the user to click a confirmation link sent to their inbox before SNS will deliver messages to them.

**IAM permissions:** `sns:Subscribe`, `sns:ListSubscriptionsByTopic`

---

### CreateTaskFunction

**Trigger:** `POST /tasks` via API Gateway  
**Purpose:** Creates a DynamoDB item with `Status = Pending` and schedules a one-time **EventBridge Scheduler** event at `now + 5 minutes`.

Key design decisions:
- The schedule name is `task-expiry-{TaskId}` — deterministic, used for cancellation later.
- `ActionAfterCompletion: DELETE` cleans up the schedule after it fires.
- The Cognito `sub` claim is used as `UserId` — never trust client-supplied user IDs.

**IAM permissions:** `dynamodb:PutItem`, `scheduler:CreateSchedule`, `iam:PassRole`

---

### GetTasksFunction

**Trigger:** `GET /tasks` via API Gateway  
**Purpose:** Queries all tasks where `UserId = <caller's sub>`. Handles DynamoDB pagination automatically.

**IAM permissions:** `dynamodb:Query`

---

### UpdateTaskFunction

**Trigger:** `PUT /tasks/{taskId}` via API Gateway  
**Purpose:** Updates `Description`, `Date`, or `Status` (only `Pending → Completed` is allowed through this endpoint). Uses a `ConditionExpression` to prevent updating another user's task.

**IAM permissions:** `dynamodb:UpdateItem`

---

### DeleteTaskFunction

**Trigger:** `DELETE /tasks/{taskId}` via API Gateway  
**Purpose:** Deletes a task. A `ConditionExpression` enforces ownership. DynamoDB Streams picks up the deletion and triggers the cancellation workflow.

**IAM permissions:** `dynamodb:DeleteItem`

---

### TaskExpiryFunction

**Trigger:** EventBridge Scheduler (at task deadline)  
**Purpose:** Conditionally updates the task to `Expired` only if `Status = Pending` (idempotent guard). If the guard fails (`ConditionalCheckFailedException`) the task was already resolved — the function exits silently.

Then publishes to SNS with a `userId` **message attribute** so the filter policy routes the email only to the task owner.

**IAM permissions:** `dynamodb:UpdateItem`, `sns:Publish`

---

### StreamProcessorFunction

**Trigger:** DynamoDB Streams (MODIFY and REMOVE events)  
**Purpose:** Bridge between DynamoDB Streams and SQS FIFO. Filters for events where a `Pending` task transitions to `Completed` or is deleted.

Uses `MessageDeduplicationId = {taskId}-cancel` to prevent duplicate cancellation messages in the FIFO queue.

**IAM permissions:** `dynamodb:GetRecords`, `dynamodb:GetShardIterator`, `sqs:SendMessage`

---

### CancellationHandlerFunction

**Trigger:** SQS FIFO queue  
**Purpose:** Deletes the EventBridge Scheduler one-time rule so the `TaskExpiryFunction` is never invoked for a resolved task.

`ResourceNotFoundException` is treated as success — the schedule may have already fired or been deleted.

Uses `ReportBatchItemFailures` so only genuinely failed messages are retried by SQS.

**IAM permissions:** `scheduler:DeleteSchedule`, `sqs:ReceiveMessage`, `sqs:DeleteMessage`

---

## Event-Driven Workflows

### Expiry workflow (happy path — task not completed in time)

```
POST /tasks
  → CreateTask λ: DynamoDB PutItem + Scheduler CreateSchedule(at deadline)
  → [5 minutes pass]
  → EventBridge fires TaskExpiry λ
  → DynamoDB UpdateItem (Pending → Expired)
  → SNS Publish → User email
```

### Cancellation workflow (task completed before deadline)

```
PUT /tasks/{id} {status: "Completed"}
  → UpdateTask λ: DynamoDB UpdateItem
  → DynamoDB Stream: MODIFY event (old=Pending, new=Completed)
  → StreamProcessor λ: SQS FIFO SendMessage {taskId}
  → CancellationHandler λ: Scheduler DeleteSchedule(task-expiry-{taskId})
```

### Cancellation workflow (task deleted before deadline)

```
DELETE /tasks/{id}
  → DeleteTask λ: DynamoDB DeleteItem
  → DynamoDB Stream: REMOVE event (old=Pending)
  → StreamProcessor λ: SQS FIFO SendMessage {taskId}
  → CancellationHandler λ: Scheduler DeleteSchedule(task-expiry-{taskId})
```

---

## Deploy to AWS

### First deploy (guided)

```bash
sam build --parallel
sam deploy --guided
```

You will be prompted for:
- Stack name — press Enter to accept `serverless-todo-app`
- Region — `us-east-1` (or your preferred region)
- Confirm IAM role creation — `y`
- Allow SAM to create S3 bucket — `y`

SAM writes your answers to `samconfig.toml` so subsequent deploys are non-interactive.

### Subsequent deploys

```bash
sam build --parallel --cached
sam deploy
```

### View stack outputs

After deploy, copy these values into the frontend `.env.local` and Amplify Console:

```bash
aws cloudformation describe-stacks \
  --stack-name serverless-todo-app \
  --query "Stacks[0].Outputs" \
  --output table
```

| Output key | Used for |
|---|---|
| `ApiUrl` | `NEXT_PUBLIC_API_URL` in frontend |
| `UserPoolId` | `NEXT_PUBLIC_USER_POOL_ID` in frontend |
| `UserPoolClientId` | `NEXT_PUBLIC_USER_POOL_CLIENT_ID` in frontend |

### Tear down

```bash
sam delete --stack-name serverless-todo-app
```

> This will delete all AWS resources including the DynamoDB table and all data.

---

## CI/CD Pipeline

The pipeline in `.github/workflows/deploy.yml` runs on every push to `main`.

### Stages

```
push to main
  └── validate job
        ├── flake8 lint (lambdas/)
        ├── OIDC credentials
        └── sam validate --lint
  └── deploy job (only on main push)
        ├── OIDC credentials
        ├── sam build --parallel --cached
        ├── sam deploy --no-confirm-changeset
        └── print stack outputs
```

### One-time AWS OIDC setup

**Step 1 — Create the GitHub OIDC Identity Provider**

In AWS Console → IAM → Identity providers → Add provider:

| Field | Value |
|---|---|
| Provider URL | `https://token.actions.githubusercontent.com` |
| Audience | `sts.amazonaws.com` |

**Step 2 — Create an IAM Role**

Trust policy (replace `ACCOUNT_ID`):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:nlenjibi/serverless-task-manager-system:*"
      }
    }
  }]
}
```

Attach `AdministratorAccess` (for the lab) or a scoped policy that covers: CloudFormation, Lambda, DynamoDB, Cognito, API Gateway, SNS, SQS, EventBridge Scheduler, IAM, S3.

**Step 3 — Add GitHub secret**

GitHub repo → Settings → Secrets → Actions → New secret:

| Name | Value |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::ACCOUNT_ID:role/GitHubActions-TodoApp` |

---

## Environment Variables

Lambda functions receive these through the SAM `Globals.Function.Environment` block. They are injected at deploy time from CloudFormation resource references — no secrets are hardcoded.

| Variable | Set on | Value source |
|---|---|---|
| `TASKS_TABLE` | All functions | `!Ref TasksTable` |
| `SNS_TOPIC_ARN` | All functions | `!Ref TaskNotificationsTopic` |
| `CANCELLATION_QUEUE_URL` | All functions | `!Ref CancellationQueue` |
| `SCHEDULER_ROLE_ARN` | CreateTask only | `!GetAtt SchedulerRole.Arn` |
| `EXPIRY_FUNCTION_ARN` | CreateTask only | `!GetAtt TaskExpiryFunction.Arn` |

---

## Observability

All Lambda functions log structured output to **CloudWatch Logs**. Each function's log group is:

```
/aws/lambda/<stack-name>-<FunctionName>
```

### Useful CloudWatch Insights queries

**Find all expiry events in the last hour:**

```sql
fields @timestamp, @message
| filter @message like /marked Expired/
| sort @timestamp desc
| limit 20
```

**Find failed cancellations:**

```sql
fields @timestamp, @message
| filter @message like /Failed to delete schedule/
| sort @timestamp desc
```

**Trace a specific task through all Lambdas:**

```sql
fields @timestamp, @logStream, @message
| filter @message like /task-id-goes-here/
| sort @timestamp asc
```

### CloudWatch Alarms (recommended additions)

Add these to `template.yaml` to monitor production health:

| Alarm | Metric | Threshold |
|---|---|---|
| Expiry failures | `TaskExpiryFunction` errors | > 0 in 5 min |
| Cancellation DLQ depth | `CancellationQueue` `ApproximateNumberOfMessagesNotVisible` | > 10 |
| API 5xx rate | API Gateway `5XXError` | > 1% over 5 min |

---

## Troubleshooting

### `sam validate` fails — circular dependency error

The `EXPIRY_FUNCTION_ARN` env var in `CreateTaskFunction` references `TaskExpiryFunction`. If SAM reports a circular dependency, ensure neither function's IAM policy or event source references the other.

### EventBridge Scheduler `AccessDeniedException`

The Scheduler needs an IAM role to invoke the Lambda (`SchedulerRole`). Verify:
1. `SchedulerRole` trust policy includes `scheduler.amazonaws.com`
2. `SchedulerRole` permissions include `lambda:InvokeFunction` on `TaskExpiryFunction`
3. `CreateTaskFunction` has `iam:PassRole` on `SchedulerRole`
4. `TaskExpiryFunction` has a Lambda resource policy allowing `scheduler.amazonaws.com` to invoke it (`TaskExpirySchedulerPermission` resource in `template.yaml`)

### SNS email never arrives

1. Check the user clicked the **subscription confirmation** link sent by SNS after first sign-in.
2. Verify the filter policy on the subscription matches the `userId` message attribute published by `TaskExpiryFunction`.
3. Check CloudWatch logs for `TaskExpiryFunction` — look for `SNS notification dispatched`.

### DynamoDB Streams not triggering `StreamProcessorFunction`

1. Confirm `StreamSpecification.StreamViewType = NEW_AND_OLD_IMAGES` in `template.yaml`.
2. Check the Lambda event source mapping is `ENABLED` in the AWS Console (Lambda → Configuration → Triggers).
3. Ensure the function's execution role has `dynamodb:GetRecords`, `dynamodb:GetShardIterator`, `dynamodb:DescribeStream`.

### Task stays `Pending` after deadline

Possible causes:
- The EventBridge Scheduler was deleted before firing (check for an early cancellation).
- The `TaskExpiryFunction` threw an error — check its CloudWatch log group.
- The task's `Status` was not `Pending` when the scheduler fired (check the conditional update guard).
