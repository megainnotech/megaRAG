# SeaweedFS
Detail…

# Architecture
…

## Sizing
SeaweedFS simply stores the Parquet files as binary blobs. It does not add extra overhead and can actually provide additional storage efficiency if we enable Erasure Coding (EC) at the SeaweedFS level, as data retention policy.

The primary data kept in SeaweedFS are:  

* Raw PromptPay transaction (PII-safe)
* CFR archival data (PII-safe)
* Predicted results with their features
  * Transaction risk score
  * Account risk score
* ML model repository
* Master data, e.g., FI code, Bank Account
* Data Analytics (Lab only)

### Summary Table 

| Dataset | Estimated size (13-month retention) |
|---|---:|
| Raw PromptPay transaction (PII-safe) | 26 TB |
| CFR archival data (PII-safe) | 400 GB |
| Predicted results with their features | 28 TB |
| ML model repository | 400 MB |
| Master data | 1 GB |
| Backup Storage | 140 GB |
| Data Analytics (Lab only) | 60 TB |
| **Total** | ~115 TB |


### Base Estimation
Any data that kept in Parquet format will be compressed with **Polars** using the **Zstd (Level 3)** algorithm.  
Why?

| Feature |	Snappy |Zstd (Level 3)|
|---|---|---|
| Write (CPU) | Blazing fast, low overhead | Moderate; tunable levels |
| Write (Network) | Slower due to larger file size | Faster due to ~39% smaller files |
| Decompression | ~3.5 GB/s | ~1.0 GB/s |
| Storage Cost | Higher (~70-80% raw compressed) | Significant savings (~80-90% raw compressed) <br> Claimed 30-40% saver compare with Snappy for Parquet files |

Verdict: In 2025, Zstd (level 3) is the superior default because its storage and network savings far outweigh the raw CPU speed advantage of Snappy.

From now on, we will use **80% compression level** for any Parquet storage sizing.

---

**Raw PromptPay transaction (PII-safe)**  
Based on Jun 2024, table below shows transaction stats:

| PP stats of monthly transaction | Value |
|---|---|
| Total account | 83,962,241  |
| Avg #of an account txn | 31.54 |
| Median | 12 |
| Max | 374 |

> ⚠️ After cut top 1% outlier off.

| PP transaction storage sizing | Value |
|---|---|
 A message size.<br>See: [schema](../txn-risk-score/index.md#promptpay-message-schema). | ~750 bytes (raw JSON) |
| Expected TPS | 5,000 |
| Transactions per month | ~13.18 billion |
| Retention | 13 months |
| Raw size per month | ~9.88 TB |
| Parquet size per month (Zstd) | ~1.98 TB |
| **Total Parquet size (13 months)** | **~26 TB** |

ℹ️ A PromptPay transaction can be either Account Lookup or Credit transfer message.

| CFR archival data (PII-safe) | Value |
|---|---|
| Today parquet dump size | 25 GB |
| Growth rate | 4% / month |
| Retention | 6 months |
| 5-year space require | ~268 GB |
| **Total w headrtoom** | **400 GB** |


**Predicted results with their features**  

| Transaction risk score | Estimated value |
|---|---|
| A score size <br> *(score 4 bytes + id 18 bytes + epoch time 4 bytes)* | 26 bytes |
| 500 features of float | 2,000 bytes |
| Avg txn per month | 50 records |
| Total account | 100 M |
| Retention period | 13 months |
| Total Raw | 137  TB |
| **Total Parquet size (ZSTD)** | **27  TB** |


TODO: Update how we do AC risk score
For now, account risk score maybe derived from txn risk score, so the txn score is its feature.

| Account risk score | Estimated value |
|---|---|
| A score size <br> *(score 4 bytes + id 18 bytes + epoch time 4 bytes)* | 26 bytes |
| Total account | 100 M |
| Retention period | 13 months |
| Total Raw | 6.17  TB |
| **Total Parquet size (ZSTD)** | **1  TB** |

---

**ML model repository**  
XGBoost model is very small. It does not require much space.

| Account risk score | Estimated value |
|---|---|
| Max model size | 10 MB |
| Max trained model per month | 8 models |
| Retention period | 24 months |
| Total JSON | 2 GB |
| **Total Parquet size (ZSTD)** | **400 MB** |


**Master data**  
There will be some small set of master data used, e.g., Bank Account info.  
Let's spare **1 GB** for this.

**Backup Storage**  
We may need to periodical backup Redis data for 2 versions.
| Redis data | Estimated value |
|---|---|
| Account Proxy | 150 GB |
| Prediction Feature | 200 GB |
| Total Raw x2 | 700 GB |
| **Total Parquet size (ZSTD)** | **140 GB** |

**Playground Storage**
60 TB

---

# Config
* Total storage: 192 TB
* Parity disk: 3
* Usable storage: 120 TB
