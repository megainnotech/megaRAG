# Redis
PrompGuard architecture is separates into real-time and batch processing parts. The real-time part mostly use Redis to make it fast and flexible.  
To make PrompGuard fast and maintain an acceptable RTO level, a proper redis persistance config is needed.

> **Use Redis Cluster as primary store, AOF `everysec`, `maxmemory ~90 GB`, `noeviction`, with  8 masters + 8 replicas.**

## Key Assumptions
- Primary data store (not just cache) for a write-heavy workload
- Writes: 2,000–5,000 TPS (inserts/updates)
- Reads: 10–50% of writes
- Some data loss acceptable (can regenerate within ~1s)
- RAM budget: up to 2 TB.
- Redis storage requirement: **~500 GB**
  - Account Proxy: 150 GB
  - Prediction Feature: 200 GB
  - Cached predicted risk score: 80 GB

### Based calculation
**Prediction feature sizing**  
*As of Dec 2025*

| 10-min raw transaction | Estimated size |
|---|---|
| 5 txns x 240 bytes x 80 M accounts | ~90 GB |
| Redis overhead | ~22GB |
| Total | ~112 GB |

> Statistic of 10-min account txn:  
> mean: 1.33 txn, median: 1, and sd: 2.61


| Daily feature | Estimated size |
|---|---|
| 300 features of float x 80 M accounts | ~90 GB |


**Account Proxy**
| Account Proxy | Estimated value |
|---|---|
| Base data from Oracle | 50 GB |
| Redis overhead | 2x–3x (due to keys, pointers, encoding) |
| Total | 150 GB RAM |

**Predicted Risk Score**

| Predicted Risk Score | Estimated value |
|---|---|
| A score size (byte) <br> *(message 150 + overhead 100)* | 250 |
| Avg txn per 10-min | 1.33 |
| Cache for (minute) | 60 |
| Total account | 80 M |
| Total size (GB) | 80 |

## Architecture & Sizing

* **Cluster mode (Redis Cluster) & Replication for HA**
  * Shard keys across multiple masters.
  * At least **1 replica per master** → automatic failover → total Redis RAM budget ≈ **1.3–1.5 TB**
* **Master maxmemory total ≈ 650–750 GB** (to safely hold 500 GB without living on the edge)


### High-level Redis Design

#### Redis Cluster Topology

* **8 masters + 8 replicas** (16 nodes total)

  * Why 8? Good balance of shard size, write throughput, and operational flexibility (resharding, maintenance, failover).

#### Memory plan

* Per node RAM: **128 GB**
* Per node `maxmemory`: **90 GB**

  * Masters total: **8 × 90 = 720 GB**
  * Enough headroom above your 500 GB requirement
  * Replicas mirror that → total Redis memory reserved ≈ **1.44 TB**

#### Hardware / ops considerations

* **Disk:** NVMe SSD strongly recommended (AOF rewrite + fsync patterns)
* **Network:** 10/25GbE preferred (cluster gossip + replication + client traffic)
* **Placement:** put each master and its replica in **different physical hosts / racks** (anti-affinity)
* **Client:** must use **cluster-aware** clients/drivers
* **Backups:** periodically copy AOF/RDB off-host if you want disaster recovery


### Durability & Data Loss

* AOF `everysec` → at most ~1 second of data loss if crash happens.
* Optional: periodic **off-box backups** (copy AOF/RDB to object storage).


## Core Redis Config Recommendations
**PER NODE** recommended config.
```conf
# Memory
maxmemory 90gb                # Leaves headroom for OS + overhead
maxmemory-policy noeviction   # Primary store: better to fail than silently drop keys

# Persistence (AOF)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec          # Good tradeoff: fast + at most ~1s data loss
no-appendfsync-on-rewrite yes # Reduce latency spikes during AOF rewrite

# RDB (optional, for faster recovery)
save 900 1
save 300 10
save 60 10000                 # Example; adjust or disable if AOF-only is fine

# Replication (example)
replica-read-only yes
# On replicas:
# replicaof <master-host> <port>

# General performance
tcp-keepalive 300
timeout 0                      # Don’t drop idle connections
protected-mode yes             # Always secure with proper binding/auth
```


## Key naming convention
Here is the key naming used entire the project: 
* Pattern: `< service_or_project_name >:< dataset >:[< id >]`
* Any part can use dash '-' as a word delimeter, e.g., `this-is-a-dataset`

**Example:**
* `promptguard:transactionscore:1234567890`
* `promptguard:feature-daily:202511`
* `promptguard:feature-realtime`


## Monitoring & Ops (Key Considerations)

* Monitor **at least**:

  * `used_memory`, `used_memory_rss`, `mem_fragmentation_ratio`
  * `instantaneous_ops_per_sec`
  * `aof_current_size`, `aof_rewrite_in_progress`
  * Replication lag, cluster state
* Alert when:

  * Memory > ~80–85% of `maxmemory`
  * Replicas are out of sync
  * AOF rewrite takes too long or fails