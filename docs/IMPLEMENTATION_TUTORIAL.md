# AI-SDLC Compass — Hands-On Implementation Tutorial

> **Audience:** Development team moving the V1 prototype into production.  
> **Goal:** Step-by-step technical guides with actual code implementations to transition from the current prototype to the Vue frontend, Kafka event-driven pipeline, and Kubernetes/GCP deployment.

---

## Table of Contents
1. [Tutorial 1: Connecting the Vue 3 Frontend to the Prototype Backend](#tutorial-1-connecting-the-vue-3-frontend)
2. [Tutorial 2: Refactoring Backend to Kafka / PubSub & Agent Workers](#tutorial-2-refactoring-backend-to-kafka--pubsub)
3. [Tutorial 3: Implementing Cloud Firestore (Replacing SQLite)](#tutorial-3-implementing-cloud-firestore)
4. [Tutorial 4: Dockerizing and Deploying to Kubernetes (GKE)](#tutorial-4-dockerizing-and-deploying-to-kubernetes)
5. [Tutorial 5: Terraform IaC & Ansible Deployment](#tutorial-5-terraform-iac--ansible-deployment)

---

## Tutorial 1: Connecting the Vue 3 Frontend

### 1.1 Project Setup
In your frontend repository or directory:
```bash
# Create Vue 3 project with Vite & TypeScript
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install
npm install axios pinia vue-router lucide-vue-next
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 1.2 Creating the API Client (`src/services/api.ts`)
Create a centralized Axios client targeting the FastAPI backend:

```typescript
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const compassApi = {
  // Step 1: Connect & Scan
  createSession: (gitUrl: string, accessToken?: string) =>
    apiClient.post('/sessions', {
      source_type: 'git',
      git_url: gitUrl,
      access_token: accessToken || null,
      consent_given: true,
    }),

  triggerScan: (sessionId: string) =>
    apiClient.post(`/sessions/${sessionId}/scan`),

  getSessionStatus: (sessionId: string) =>
    apiClient.get(`/sessions/${sessionId}`),

  // Step 2: Review Signals
  getSignals: (sessionId: string) =>
    apiClient.get(`/sessions/${sessionId}/signals`),

  patchSignals: (sessionId: string, patchedGroups: Record<string, any>) =>
    apiClient.patch(`/sessions/${sessionId}/signals`, { signal_groups: patchedGroups }),

  confirmSignals: (sessionId: string) =>
    apiClient.post(`/sessions/${sessionId}/confirm-signals`),

  // Step 3: Diagnostic Conversation
  startDiagnostic: (sessionId: string) =>
    apiClient.post(`/sessions/${sessionId}/diagnose`),

  sendChatMessage: (sessionId: string, content: string, questionIds?: string[]) =>
    apiClient.post(`/sessions/${sessionId}/conversation`, {
      content,
      responding_to_questions: questionIds || [],
    }),

  getKnowledgeGaps: (sessionId: string) =>
    apiClient.get(`/sessions/${sessionId}/knowledge-gaps`),

  saveDraft: (sessionId: string) =>
    apiClient.put(`/sessions/${sessionId}/draft`),

  continueDiagnostic: (sessionId: string) =>
    apiClient.post(`/sessions/${sessionId}/continue-diagnostic`),

  // Step 4: Report
  getReport: (sessionId: string) =>
    apiClient.get(`/sessions/${sessionId}/report`),
};
```

### 1.3 Setting up the WebSocket for Live Agent Chat (`src/composables/useDiagnosticSocket.ts`)
For the real-time chat in Step 3 (Figma Screen 3):

```typescript
import { ref } from 'vue';

export function useDiagnosticSocket(sessionId: string) {
  const messages = ref<any[]>([]);
  const agentStatuses = ref<Record<string, any>>({});
  const isAgentThinking = ref(false);
  let socket: WebSocket | null = null;

  const connect = () => {
    socket = new WebSocket(`ws://localhost:8000/api/v1/sessions/ws/${sessionId}/conversation`);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'initial_state') {
        messages.value = data.messages;
        agentStatuses.value = data.agent_statuses;
      } else if (data.type === 'agent_message') {
        messages.value.push(data.message);
        isAgentThinking.value = false;
      } else if (data.type === 'agent_status') {
        if (data.status === 'agents_processing') {
          isAgentThinking.value = true;
        } else if (data.agents) {
          agentStatuses.value = data.agents;
          isAgentThinking.value = false;
        }
      }
    };
  };

  const sendMessage = (content: string, respondingTo: string[] = []) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    
    // Add local optimistic message
    messages.value.push({ role: 'user', content });

    socket.send(JSON.stringify({
      type: 'user_message',
      content,
      responding_to_questions: respondingTo,
    }));
  };

  const disconnect = () => {
    if (socket) socket.close();
  };

  return { messages, agentStatuses, isAgentThinking, connect, sendMessage, disconnect };
}
```

---

## Tutorial 2: Refactoring Backend to Kafka / PubSub

In the current prototype, `backend/orchestrator/supervisor.py` runs agents in-process via `asyncio.gather`. Here is how to evolve this to Kafka or Google Cloud Pub/Sub.

### 2.1 Installing Kafka Dependencies
Add to `backend/requirements.txt`:
```txt
aiokafka>=0.10.0
```

### 2.2 Event Producer (`backend/events/producer.py`)
Create a persistent async event publisher:

```python
import json
import logging
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

class EventProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8")
        )
        await self._producer.start()

    async def publish(self, topic: str, event_data: dict):
        if not self._producer:
            await self.start()
        await self._producer.send_and_wait(topic, event_data)
        logger.info(f"Published event to topic '{topic}': {event_data.get('event_type')}")

    async def stop(self):
        if self._producer:
            await self._producer.stop()

# Global singleton
event_bus = EventProducer()
```

### 2.3 Refactoring `scan.py` to Publish `repo.scanned`
In `backend/api/scan.py`, replace direct synchronous completion with an event:

```python
# In backend/api/scan.py inside execute_scan_task():
from ..events.producer import event_bus

# Run Light Scanner
scan_result = run_light_scanner(workspace_path=ws_path, repo_info=repo_info)
session.scanner_output = scan_result.model_dump(mode="json")
await store.update_session(session)

# PUBLISH EVENT TO KAFKA
await event_bus.publish("repo.scanned", {
    "event_type": "REPOSITORY_SCANNED",
    "session_id": session.id,
    "scanner_output": session.scanner_output
})
```

### 2.4 Creating Specialist Agent Consumer Workers (`backend/workers/qa_worker.py`)
Each specialist agent runs as an independent worker pod consuming events:

```python
import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from backend.agents.qa_agent import QAAgent
from backend.llm import get_llm_provider
from backend.storage import get_storage
from backend.events.producer import event_bus

logger = logging.getLogger("qa_worker")

async def run_qa_worker():
    consumer = AIOKafkaConsumer(
        "repo.scanned",
        bootstrap_servers="localhost:9092",
        group_id="qa_specialist_group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )
    await consumer.start()
    agent = QAAgent(get_llm_provider())
    store = await get_storage()

    logger.info("QA Specialist Agent Worker listening on 'repo.scanned'...")
    try:
        async for msg in consumer:
            event = msg.value
            session_id = event["session_id"]
            profile = await store.get_profile(session_id)
            
            # Execute QA 3-phase analysis
            qa_results = await agent.run_full_cycle(profile)
            
            # Publish completion event
            await event_bus.publish("agent.evaluated", {
                "event_type": "SPECIALIST_EVALUATED",
                "session_id": session_id,
                "domain": "qa_testing",
                "results": qa_results
            })
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run_qa_worker())
```

---

## Tutorial 3: Implementing Cloud Firestore (Replacing SQLite)

The prototype defines the abstract class `BaseStore` in `backend/storage/base_store.py`. You do not need to change any business logic or agent code—simply implement the interface using `google-cloud-firestore`.

### 3.1 Install Cloud Firestore SDK
```bash
pip install google-cloud-firestore
```

### 3.2 Create `backend/storage/firestore_store.py`

```python
from google.cloud import firestore
from backend.models.diagnostic_session import DiagnosticSession
from backend.models.contextual_profile import ContextualProfile
from backend.storage.base_store import BaseStore

class FirestoreStore(BaseStore):
    def __init__(self, project_id: str | None = None):
        self.db = firestore.AsyncClient(project=project_id)
        self.sessions_col = self.db.collection("diagnostic_sessions")
        self.profiles_col = self.db.collection("contextual_profiles")

    async def initialize(self) -> None:
        pass  # Firestore is serverless; no table schemas required

    async def save_session(self, session: DiagnosticSession) -> None:
        doc_ref = self.sessions_col.document(session.id)
        await doc_ref.set(session.model_dump(mode="json"))

    async def get_session(self, session_id: str) -> DiagnosticSession | None:
        doc = await self.sessions_col.document(session_id).get()
        if not doc.exists:
            return None
        return DiagnosticSession.model_validate(doc.to_dict())

    async def update_session(self, session: DiagnosticSession) -> None:
        await self.save_session(session)

    async def list_sessions(self, limit: int = 50) -> list[DiagnosticSession]:
        query = self.sessions_col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        docs = [doc async for doc in query.stream()]
        return [DiagnosticSession.model_validate(d.to_dict()) for d in docs]

    async def delete_session(self, session_id: str) -> bool:
        await self.sessions_col.document(session_id).delete()
        await self.profiles_col.document(session_id).delete()
        return True

    async def save_profile(self, profile: ContextualProfile) -> None:
        await self.profiles_col.document(profile.session_id).set(profile.model_dump(mode="json"))

    async def get_profile(self, session_id: str) -> ContextualProfile | None:
        doc = await self.profiles_col.document(session_id).get()
        if not doc.exists:
            return None
        return ContextualProfile.model_validate(doc.to_dict())

    async def close(self) -> None:
        self.db.close()
```

### 3.3 Activate in `backend/storage/__init__.py`
Update `get_storage()`:
```python
import os
from .base_store import BaseStore
from .sqlite_store import SQLiteStore

async def get_storage() -> BaseStore:
    global _store
    if _store is None:
        if os.getenv("USE_FIRESTORE", "false").lower() == "true":
            from .firestore_store import FirestoreStore
            _store = FirestoreStore()
        else:
            _store = SQLiteStore()
            await _store.initialize()
    return _store
```

---

## Tutorial 4: Dockerizing and Deploying to Kubernetes (GKE)

### 4.1 Production `Dockerfile` (`backend/Dockerfile`)

```dockerfile
FROM python:3.12-slim

# Install system dependencies (git for scanning)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . /app/backend

ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 Kubernetes Deployment Manifest (`k8s/api-deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compass-api
  namespace: default
  labels:
    app: compass-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: compass-api
  template:
    metadata:
      labels:
        app: compass-api
    spec:
      containers:
      - name: api
        image: gcr.io/PROJECT_ID/compass-backend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: LLM_PROVIDER
          value: "google"
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: compass-secrets
              key: google-api-key
        - name: USE_FIRESTORE
          value: "true"
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: compass-api-service
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: compass-api
```

---

## Tutorial 5: Terraform IaC & Ansible Deployment

### 5.1 Terraform Provisioning GKE & Firestore (`terraform/main.tf`)

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. VPC Network
resource "google_compute_network" "vpc" {
  name                    = "compass-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "compass-subnet"
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.0.0.0/20"
}

# 2. GKE Cluster (Autopilot for Zero Node Maintenance)
resource "google_container_cluster" "primary" {
  name             = "compass-gke-cluster"
  location         = var.region
  enable_autopilot = true
  network          = google_compute_network.vpc.name
  subnetwork       = google_compute_subnetwork.subnet.name
}

# 3. Cloud Firestore Database
resource "google_firestore_database" "database" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# 4. GCS Bucket for Uploaded Archives and PDF Reports
resource "google_storage_bucket" "reports" {
  name          = "${var.project_id}-compass-artifacts"
  location      = var.region
  force_destroy = false
  uniform_bucket_level_access = true
}
```

### 5.2 Ansible Host Setup Playbook (`ansible/setup_runner.yml`)
For configuring automated CI/CD runners and deployment tools:

```yaml
---
- name: Configure CI/CD Worker Node
  hosts: build_servers
  become: yes
  tasks:
    - name: Install required system packages
      apt:
        name:
          - git
          - docker.io
          - python3-pip
          - kubectl
        state: present
        update_cache: yes

    - name: Ensure docker service is running
      systemd:
        name: docker
        state: started
        enabled: yes

    - name: Authenticate Google Cloud SDK for GKE deployment
      command: gcloud container clusters get-credentials compass-gke-cluster --region europe-west1
```

---

## Summary Checklist
- [x] Prototype backend running and verified locally
- [ ] Connect Vue 3 application using `src/services/api.ts`
- [ ] Implement WebSocket hook `useDiagnosticSocket.ts` in Vue chat screen
- [ ] Deploy Kafka/PubSub and split workers into Docker containers
- [ ] Switch `BaseStore` to `FirestoreStore`
- [ ] Apply `terraform/main.tf` to provision GKE and cloud services
