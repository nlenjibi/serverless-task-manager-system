# Architecture Diagram

> All diagrams are written in [Mermaid](https://mermaid.js.org/) and render natively on GitHub.

---

## 1. High-Level System Overview

```mermaid
graph TD
    subgraph Client["🌐 Client — AWS Amplify (Next.js)"]
        UI["Task Dashboard"]
    end

    subgraph Auth["🔐 Authentication"]
        COGN["Amazon Cognito\nUser Pool"]
        PRE["PreSignUp λ\n(auto-confirm)"]
        POST["PostAuthentication λ\n(SNS subscribe)"]
    end

    subgraph API["📡 API Layer"]
        APIGW["API Gateway\nREST — Cognito Authorizer"]
    end

    subgraph Compute["⚙️ Compute — Lambda"]
        CREATE["CreateTask λ"]
        GET["GetTasks λ"]
        UPDATE["UpdateTask λ"]
        DELETE["DeleteTask λ"]
        EXPIRY["TaskExpiry λ"]
        STREAM["StreamProcessor λ"]
        CANCEL["CancellationHandler λ"]
    end

    subgraph Data["🗄️ Data"]
        DDB["DynamoDB\nTasks Table\n(on-demand + Streams)"]
    end

    subgraph Events["📅 Event Bus"]
        SCHED["EventBridge Scheduler\n(per-task one-time rule)"]
        SQS["SQS FIFO\nCancellation Queue"]
    end

    subgraph Notify["📧 Notifications"]
        SNS["SNS Topic\nTask Notifications"]
        EMAIL["User Email\n(per-user filter policy)"]
    end

    subgraph Observe["🔍 Observability"]
        CW["CloudWatch\nLogs & Metrics"]
    end

    UI -- "HTTPS + ID token" --> APIGW
    UI -- "signUp / signIn" --> COGN

    COGN -- "PreSignUp trigger" --> PRE
    COGN -- "PostAuthentication trigger" --> POST
    POST -- "sns:Subscribe (email + filter)" --> SNS

    APIGW --> CREATE & GET & UPDATE & DELETE

    CREATE -- "PutItem" --> DDB
    GET -- "Query" --> DDB
    UPDATE -- "UpdateItem" --> DDB
    DELETE -- "DeleteItem" --> DDB

    CREATE -- "CreateSchedule\n(at deadline)" --> SCHED

    SCHED -- "Invoke at deadline" --> EXPIRY
    EXPIRY -- "UpdateItem (Pending→Expired)" --> DDB
    EXPIRY -- "Publish + userId filter" --> SNS

    SNS -- "Filtered email" --> EMAIL

    DDB -- "Stream (MODIFY / REMOVE)" --> STREAM
    STREAM -- "SendMessage (FIFO)" --> SQS
    SQS -- "Trigger" --> CANCEL
    CANCEL -- "DeleteSchedule" --> SCHED

    Compute --> CW
```

---

## 2. User Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant Next.js
    participant Cognito
    participant PreSignUp as PreSignUp λ
    participant PostAuth as PostAuth λ
    participant SNS

    User->>Next.js: Fill register form
    Next.js->>Cognito: signUp(email, password)
    Cognito->>PreSignUp: PreSignUp trigger
    PreSignUp-->>Cognito: autoConfirmUser = true
    Cognito-->>Next.js: User confirmed ✓

    User->>Next.js: Fill login form
    Next.js->>Cognito: signIn(email, password)
    Cognito->>PostAuth: PostAuthentication trigger
    PostAuth->>SNS: subscribe(email, filterPolicy={userId})
    SNS-->>User: "Confirm subscription" email
    Cognito-->>Next.js: ID token + Access token
    Next.js->>Next.js: Store session, redirect → dashboard
```

---

## 3. Task Creation & Expiry Flow

```mermaid
sequenceDiagram
    actor User
    participant API as API Gateway
    participant CreateLambda as CreateTask λ
    participant DDB as DynamoDB
    participant Scheduler as EventBridge Scheduler
    participant ExpiryLambda as TaskExpiry λ
    participant SNS

    User->>API: POST /tasks {description, date}
    API->>CreateLambda: event (JWT claims = UserId)
    CreateLambda->>DDB: PutItem {Status: Pending, Deadline: now+5min}
    CreateLambda->>Scheduler: CreateSchedule at(deadline)\ntarget = TaskExpiry λ
    CreateLambda-->>User: 201 {task}

    Note over Scheduler: ⏱ 5 minutes elapse

    Scheduler->>ExpiryLambda: {taskId, userId}
    ExpiryLambda->>DDB: UpdateItem (ConditionExpr: Status = Pending)\n→ Status = Expired
    alt Task was still Pending
        ExpiryLambda->>SNS: Publish "Task Expired" + userId attribute
        SNS-->>User: 📧 Email notification
    else Task already Completed / Deleted
        ExpiryLambda-->>ExpiryLambda: ConditionalCheckFailed — skip
    end
```

---

## 4. Expiry Cancellation Flow (DynamoDB Streams → SQS FIFO → Lambda)

```mermaid
sequenceDiagram
    actor User
    participant API as API Gateway
    participant UpdateLambda as UpdateTask λ / DeleteTask λ
    participant DDB as DynamoDB
    participant Stream as DynamoDB Stream
    participant StreamProc as StreamProcessor λ
    participant SQS as SQS FIFO Queue
    participant CancelLambda as CancellationHandler λ
    participant Scheduler as EventBridge Scheduler

    User->>API: PUT /tasks/{id} {status: Completed}\nor DELETE /tasks/{id}
    API->>UpdateLambda: event
    UpdateLambda->>DDB: UpdateItem / DeleteItem
    DDB-->>Stream: MODIFY or REMOVE record\n(OLD: Pending → NEW: Completed)

    Stream->>StreamProc: Batch of stream records
    StreamProc->>StreamProc: Filter: old=Pending AND\n(new=Completed OR REMOVE event)
    StreamProc->>SQS: SendMessage {taskId}\nMessageGroupId=userId\nDeduplicationId=taskId-cancel

    SQS->>CancelLambda: Trigger (batch=1)
    CancelLambda->>Scheduler: DeleteSchedule(task-expiry-{taskId})
    alt Schedule exists
        Scheduler-->>CancelLambda: ✓ Deleted
    else Schedule already fired
        Scheduler-->>CancelLambda: ResourceNotFoundException → ignored
    end
```

---

## 5. IAM Trust & Permissions Model

```mermaid
graph LR
    subgraph GitHub["GitHub Actions (OIDC)"]
        WF["deploy.yml\nworkflow"]
    end

    subgraph AWS_IAM["AWS IAM"]
        OIDCP["OIDC Provider\ntoken.actions.githubusercontent.com"]
        ROLE["GitHubActions-TodoApp Role\nsts:AssumeRoleWithWebIdentity"]
    end

    subgraph Services["AWS Services"]
        CFN["CloudFormation"]
        S3["S3 (SAM artifacts)"]
        LAMBDA["Lambda"]
        DDB2["DynamoDB"]
        COGN2["Cognito"]
        APIGW2["API Gateway"]
        SNS2["SNS"]
        SQS2["SQS"]
        EB["EventBridge Scheduler"]
    end

    subgraph LambdaRoles["Lambda Execution Roles (least-privilege)"]
        CREATE_R["CreateTask role\ndynamodb:PutItem\nscheduler:CreateSchedule\niam:PassRole"]
        EXPIRY_R["TaskExpiry role\ndynamodb:UpdateItem\nsns:Publish"]
        STREAM_R["StreamProcessor role\nsqs:SendMessage\ndynamodb:GetRecords"]
        CANCEL_R["CancellationHandler role\nscheduler:DeleteSchedule\nsqs:DeleteMessage"]
    end

    WF -- "AssumeRoleWithWebIdentity\n(repo condition)" --> OIDCP
    OIDCP --> ROLE
    ROLE --> CFN & S3 & LAMBDA & DDB2 & COGN2 & APIGW2 & SNS2 & SQS2 & EB

    LAMBDA --> CREATE_R & EXPIRY_R & STREAM_R & CANCEL_R
```

---

## 6. Data Model

```mermaid
erDiagram
    TASKS {
        string UserId PK "Cognito sub (partition key)"
        string TaskId SK "UUID (sort key)"
        string Description "Task text"
        string Date "YYYY-MM-DD"
        string Status "Pending | Completed | Expired"
        string Deadline "ISO-8601 — now + 5 min"
        string CreatedAt "ISO-8601"
        string UpdatedAt "ISO-8601"
        string UserEmail "Owner email (denormalised)"
    }
```

**Access patterns supported by the primary key:**

| Pattern | Operation |
|---|---|
| List all tasks for a user | `Query(UserId = :uid)` |
| Get / update / delete one task | `GetItem / UpdateItem / DeleteItem(UserId, TaskId)` |
| Expiry handler writes | `UpdateItem(UserId, TaskId)` with condition `Status = Pending` |
