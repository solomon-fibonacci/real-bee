# System Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                      │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Web App   │  │  Mobile App │  │  Python SDK │  │   Other API │         │
│  │ (React/Vue) │  │   (Swift)   │  │   (httpx)   │  │   Clients   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                │                  │
│         │  REST API      │  WebSocket     │   REST API     │   REST API      │
│         │  (JSON)        │  (JSON)        │   (JSON)       │   (JSON)        │
└─────────┼────────────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI APPLICATION LAYER                             │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                    AUTO-GENERATED ROUTES                             │    │
│  │                                                                      │    │
│  │  POST   /entities         │  GET    /entities/{id}                 │    │
│  │  GET    /entities         │  PATCH  /entities/{id}                 │    │
│  │  DELETE /entities/{id}    │  POST   /entities/bulk                 │    │
│  │  POST   /entities/search  │  WS     /ws/entities                   │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                    CRUD FRAMEWORK (framework.py)                     │    │
│  │                                                                      │    │
│  │  • Route Generation        • Validation (Pydantic)                  │    │
│  │  • Lifecycle Hooks         • Error Handling                         │    │
│  │  • Schema Registration     • Response Serialization                 │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
└─────┬──────────────────┬──────────────────┬──────────────────┬───────────────┘
      │                  │                  │                  │
      │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   DATABASE  │  │   EVENTS    │  │   SEARCH    │  │  WEBSOCKET  │
│   MANAGER   │  │     BUS     │  │   ENGINE    │  │   MANAGER   │
└─────┬───────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
      │                 │                 │                 │
      │                 │                 │                 │
┌───────────────────────────────────────────────────────────────────────────────┐
│                            DATA PERSISTENCE LAYER                              │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐   │
│  │     PostgreSQL       │  │     Redis Cache      │  │   FAISS Index    │   │
│  ├──────────────────────┤  ├──────────────────────┤  ├──────────────────┤   │
│  │                      │  │                      │  │                  │   │
│  │ • Primary Storage    │  │ • Result Caching     │  │ • Vector Index   │   │
│  │ • JSONB + Columns    │  │ • Session Storage    │  │ • IndexFlatIP    │   │
│  │ • B-tree Indices     │  │ • Pub/Sub Channel    │  │ • IndexIVFFlat   │   │
│  │ • GIN Indices        │  │ • Event History      │  │ • GPU Support    │   │
│  │ • Connection Pool    │  │ • Connection Pool    │  │ • Persistence    │   │
│  │                      │  │                      │  │                  │   │
│  │ ┌──────────────┐     │  │ ┌──────────────┐     │  │ ┌──────────┐     │   │
│  │ │   Entity     │     │  │ │   Cache      │     │  │ │  Vector  │     │   │
│  │ │   Tables     │     │  │ │   Keys       │     │  │ │  Indices │     │   │
│  │ └──────────────┘     │  │ └──────────────┘     │  │ └──────────┘     │   │
│  │ ┌──────────────┐     │  │ ┌──────────────┐     │  │ ┌──────────┐     │   │
│  │ │   Indices    │     │  │ │   Pub/Sub    │     │  │ │   ID      │     │   │
│  │ └──────────────┘     │  │ └──────────────┘     │  │ │ Mapping  │     │   │
│  │                      │  │                      │  │ └──────────┘     │   │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘   │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                            AI/ML PROCESSING LAYER                              │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                         CLIP MODEL (OpenAI)                          │    │
│  │                                                                      │    │
│  │  ┌─────────────────┐                    ┌─────────────────┐         │    │
│  │  │  Text Encoder   │                    │  Image Encoder  │         │    │
│  │  │   (ViT-B/32)    │                    │   (ViT-B/32)    │         │    │
│  │  └────────┬────────┘                    └────────┬────────┘         │    │
│  │           │                                      │                  │    │
│  │           └──────────────┬───────────────────────┘                  │    │
│  │                          ▼                                          │    │
│  │                   512-dim Embedding                                 │    │
│  │                   (L2 Normalized)                                   │    │
│  │                                                                      │    │
│  │  • Multimodal Embeddings (Text + Image)                            │    │
│  │  • Batch Processing                                                 │    │
│  │  • GPU Acceleration                                                 │    │
│  │  • Thread Pool Executor                                            │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────────┐
│                              EVENT FLOW DIAGRAM                                │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  1. CREATE ENTITY                                                             │
│     ─────────────                                                             │
│     Client ──[POST /entities]──> FastAPI                                      │
│                                     │                                          │
│                                     ├──> Validate (Pydantic)                  │
│                                     ├──> before_create() Hook                 │
│                                     ├──> Insert DB (PostgreSQL)               │
│                                     ├──> Generate Embedding (CLIP)            │
│                                     ├──> Index Vector (FAISS)                 │
│                                     ├──> Cache Result (Redis)                 │
│                                     ├──> Emit Event (EventBus)                │
│                                     │      │                                   │
│                                     │      └──> Redis Pub/Sub                 │
│                                     │             │                            │
│                                     │             ├──> EventHistory           │
│                                     │             └──> WebSocket Broadcast    │
│                                     │                     │                    │
│                                     │                     └──> All Subscribers │
│                                     ├──> after_create() Hook                  │
│                                     └──> Return Response                      │
│                                                                                │
│  2. MULTIMODAL SEARCH                                                         │
│     ─────────────────                                                         │
│     Client ──[POST /entities/search]──> FastAPI                               │
│                  {"text": "...", "image_url": "..."}                          │
│                                     │                                          │
│                                     ├──> Load CLIP Model                      │
│                                     ├──> Encode Text (CLIP)                   │
│                                     ├──> Encode Image (CLIP)                  │
│                                     ├──> Combine Embeddings (weighted avg)    │
│                                     ├──> Search FAISS Index                   │
│                                     │      (Cosine Similarity)                 │
│                                     ├──> Get Top-K Results                    │
│                                     ├──> Fetch Entities from Cache/DB         │
│                                     └──> Return Results + Scores              │
│                                                                                │
│  3. REAL-TIME UPDATE                                                          │
│     ────────────────                                                          │
│     Client ──[WS /ws/entities]──> FastAPI                                     │
│                                     │                                          │
│                                     ├──> Accept WebSocket                     │
│                                     ├──> Register Connection                  │
│                                     ├──> Subscribe to Entity Events           │
│                                     │                                          │
│     [Another Client Updates Entity]                                           │
│                                     │                                          │
│                                     ├──> Event Published (EventBus)           │
│                                     ├──> Redis Pub/Sub Broadcast              │
│                                     ├──> WebSocketManager Receives            │
│                                     └──> Broadcast to All Subscribers         │
│                                            │                                   │
│     Client <──[WS Message]────────────────┘                                   │
│     {"type": "event", "data": {...}}                                          │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────────┐
│                         SCALABILITY & DEPLOYMENT                               │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│                            ┌──────────────┐                                   │
│                            │ Load Balancer│                                   │
│                            │   (Nginx)    │                                   │
│                            └───────┬──────┘                                   │
│                                    │                                           │
│                   ┌────────────────┼────────────────┐                         │
│                   │                │                │                         │
│          ┌────────▼───────┐ ┌─────▼────────┐ ┌────▼─────────┐               │
│          │   App Server   │ │ App Server   │ │ App Server   │               │
│          │   Instance 1   │ │ Instance 2   │ │ Instance 3   │               │
│          │   (Docker)     │ │  (Docker)    │ │  (Docker)    │               │
│          └────────┬───────┘ └─────┬────────┘ └────┬─────────┘               │
│                   │                │                │                         │
│                   └────────────────┼────────────────┘                         │
│                                    │                                           │
│              ┌────────────────────┼────────────────────┐                     │
│              │                    │                    │                     │
│     ┌────────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐            │
│     │   PostgreSQL    │  │  Redis Cluster │  │  FAISS Shards  │            │
│     │   (Primary +    │  │  (3 Nodes)     │  │  (Distributed) │            │
│     │   Replicas)     │  │                │  │                │            │
│     └─────────────────┘  └────────────────┘  └────────────────┘            │
│                                                                                │
│  Performance Characteristics:                                                 │
│  • Horizontal scaling via load balancer                                       │
│  • Sticky sessions for WebSocket connections                                  │
│  • Redis Cluster for distributed pub/sub                                      │
│  • PostgreSQL read replicas for read-heavy workloads                         │
│  • FAISS index sharding for large vector datasets                            │
│  • Docker containers for easy deployment                                      │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
```
