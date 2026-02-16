# High Level Design
This section will provide you broad vision of the system.

## C1 – Context

![Lab Context Diagram](images/pg-c1.png "Lab Context Diagram")


## C2 – Container Diagram
 
![Lab Container Diagram](images/pg-c2.png "Lab Container Diagram")

### High Level design

**Transaction Risk Score**
```mermaid
graph TD

  subgraph "Sender Bank"
    A["Sender Bank<br>(API Call)"]
    F{"Risk Score Decision<br>(Allow / Challenge / Block)"}
  end

  A --> B["Risk Scoring API<br>(REST)"]
  PPL["PromptPay Logging<br>(promptail -> Loki)"] --> G["Kafka<br>(Transaction Logging)"]

  %% Transaction Request Flow
  subgraph "Score Serving"
    B --> Get_cached["Get cached score<br>(Redis)"]
    Get_cached --> CON1{"Found?"}
    E["API Response to Sender Bank"]
  end

  CON1 -- Yes --> E
  D --> E
  E -- (<100ms Total Round Trip) --> F

  subgraph "Real-Time Scoring Core"
    FT_UD
    CON1 -- No --> C["Feature Lookup<br>(Redis)"]
    C --> D["Model Inference<br>(Python)"]
    D --> Cache_score["Cache Score<br>(Redis)"]
  end
  
%% Batch and Analytics
  subgraph "Batch Pipeline"
    H --> K["Model Training<br>(Python, Spark)"]
    H --> L["Fraud Trail Analysis<br>Graph Traversals"]
    K --> M["Model Registry<br>(Versioned Models)"]
    M --> D
    L --> J["Feature Store Updates<br>(for future scoring)"]
  end

  %% Async Processing and Logging
  G -- predict score --> C
  G -- update account profile --> FT_UD["Feature Update<br>(Redis)"]
  G --> H["Data Lake<br>(Parquet)"]

  %% Monitoring & MLOps
%%  B -.-> N["Prometheus / Grafana<br>Latency & Health Metrics"]
%%  D -.-> N
%%  K -.-> O["Model Metrics & Drift Detection"]
  %% comment below to make it easier to read (the monitor is needed both real-time and batch)
  %% K -.-> N
  %% H -.-> N
  %% L -.-> N

  style Get_cached fill:#a5a,stroke:#333,stroke-width:2px
  style Cache_score fill:#a5a,stroke:#333,stroke-width:2px
  style D fill:#88a,stroke:#333
  style A fill:#595,stroke:#333
  style E fill:#595,stroke:#333
  style F fill:#595,stroke:#333
```


## C3 – Component Diagram
 
![Lab Component Diagram](images/pg-c3.png "Lab Component Diagram")

### List of Components

![Lab Component Diagram](images/pg-c3-number.png "Lab Component Diagram")
Later in this doc, we will provide more information of each component following:

1. Blendata PromptPay fetcher
2. Apigee API gateway
3. ITMX SSO integration
4. Jupyter Hub
5.  Transaction risk score service
    1. API service
    2. Core Prediction Service
    3. Redis feature store
    4. Kafka topic
    5. Real-time Transaction Data Preparation
    6. File Storage: Model Repo, Prediction Result Store
6.  Account risk score service
    1. API service
    2. Database & Data model
    3. Prediction Pipeline
    4. Redis feature
    5. File Storage: Master data, Model Repo, Prediction Result Store
7.  Data Preparation Pipeline
    1. Pipeline Spec
    2. Data for training
    3. Feature data for prediction: CFR, PromptPay
       1. Feature snapshot (for evaluation)
8.  Model Training Pipeline
    1. Pipeline Spec
    2. File Storage: Model Repo
9.  Model Evaluation Pipeline
    1. Pipeline Spec
    2. File Storage:
        1. Model Repo
        2. Prediction Result Store (transaction and account score)
        3. CFR answer
        4. Feature snapshot of existing model
        5. Current Feature data
    3. Database & Data model to keep evaluation result
    4. Grafana dashboard
10. Fraud Hub
    1. Web spec
    2. Database
    3. File Storage



## C3 – Component Diagram (Production Environment)
 
For Prod Environment, please refer to: PromptGuard-TRS-Internal-Prod Technical Specification.  
*TODO give link*

![Prod Component Diagram](images/pg-c3-prod.png "Prod Component Diagram")
 
# Appendix
## I: Best practice of fraud risk score architecture
Refer to a GPT research: [link](https://chatgpt.com/share/693b94e6-1ab8-800f-9e51-006eaa1f26bd)

```mermaid
graph TD
  %% Transaction Request Flow
  A["Sender Bank<br>(API Call)"] --> B["Risk Scoring API<br>(REST/gRPC)"]

  subgraph "Real-Time Scoring Core"
    B --> C["Feature Lookup<br>(Redis/In-Mem Cache)"]
    B --> D["Model Inference<br>(TensorFlow Serving / Go Service)"]
    C --> D
    D --> E{"Risk Score Decision<br>(Allow / Challenge / Block)"}
  end

  E --> F["API Response to Sender Bank<br>(<100ms Total Round Trip)"]

  %% Async Processing and Logging
  B --> G["Kafka / Message Bus<br>(Transaction Logging)"]
  G --> H["Data Lake<br>(Parquet, ClickHouse)"]
  G --> I["Graph DB<br>(Neo4j, TigerGraph)"]
  G --> J["Feature Store Updates<br>(for future scoring)"]

  %% Batch and Analytics
  subgraph "Batch Pipeline"
    H --> K["Model Training<br>(Python, Spark)"]
    I --> L["Fraud Ring Analysis<br>Graph Traversals"]
    K --> M["Model Registry<br>(Versioned Models)"]
    M --> D
    L --> J
  end

  %% Monitoring & MLOps
  B -.-> N["Prometheus / Grafana<br>Latency & Health Metrics"]
  D -.-> N
  K -.-> O["Model Metrics & Drift Detection"]
  %% comment below to make it easier to read (the monitor is needed both real-time and batch)
  %% K -.-> N
  %% H -.-> N
  %% L -.-> N

  style B fill:#a5a,stroke:#333,stroke-width:2px
  style D fill:#88a,stroke:#333
  style E fill:#595,stroke:#333
  style F fill:#595,stroke:#333
```


## II: Lab Environment Hardware Specification
As of 2025, we awarded Yip In Tsoi as the HW provider and BlueBik as the system intefrator of the lab environment.

Here is the hardware spec and SI work scope:

| Hardware Spec | QTY.  | SI Work Scope  | Note |
|---|:---:|---|---|
| **Lab Servers** <br> CPU: 168 Core <br> RAM: 2560 GB <br> GPU: Nvdia L40S 48GB RAM <br> Storage: 2x 1.6 TB SSD SAS 24 Gbps RAID 1 <br> OS: CentOS | 3 | **Kubernetes deployment** <br> - Install k8s foundation (v1.32+, Containerd, Flannel, Nginx IC) <br> - Master & Worker on all 3 nodes <br> - UI: Kubernetes Dashboard or similar <br> - Configure audit log to local storage <br> <br> **Analytics Hub Deployment** <br> - Apache Airflow <br> - PySpark <br> - Cassandra <br> - DBT or another data transformation tool <br> - Other components as bidder propose | **Total spec** <br> CPU: 504 Core <br> RAM: 7680 GB <br> Storage: 9.6 TB |
| **FileSystem Server** <br> CPU: 64 Core <br> RAM: 512 GB <br> OS Disk: 2x 800GB SSD SAS 24 Gbps RAID1 <br> Storage: 8x SAS HDD / 12 Gbps 7200rpm 24TB <br> OS:   CentOS | 1 | SeaweedFS deployment | Total Storage: 192 TB <br> * After configured parity disks, usable storage will be lower. |

