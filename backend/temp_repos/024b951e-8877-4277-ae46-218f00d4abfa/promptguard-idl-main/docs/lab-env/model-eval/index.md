# Model Evaluation Pipeline
PromptGuard is designed to self maintaining in term of model performance.
It will periodically evaluate and update prediction models.

![Model Evaluation Pipeline Component Diagram](images/eval-c3.png "Model Evaluation Pipeline Component Diagram")

We can evaluate both model performance and how much users follow our score suggestion (trust the score).
To evaluate how user trust our scores, we can use high risk score PromptPay proxy lookup vs credit transfer transaction. If they believe the score, there will be less credit transfer transaction than the lookup.

But later on in this doc, we will focus on how to evaluate the model performance.

## Conceptual flow
Below is a conceptual flow of the model evaluation pipeline and performance maintainance.

```mermaid
flowchart TD
    T_auto([Schedule Trigger]) --> SD[Check PP data statistical diff]
    T_manual([Manual Trigger]) --> SD
    T_auto --> find_new[Regulary train new challenger models]
    find_new --> chal_model[new model w current features]
    SD --> cond_sd_diff{diif > threshold α}
    cond_sd_diff -- No --> ending([End])
    cond_sd_diff -- Yes --> noti@{ shape: display, label: "Notify to admin"}

    T_auto([Schedule Trigger]) --> model_eval[Test model performance]
    T_manual([Manual Trigger]) --> model_eval
    model_eval --> cond_model_diff{performance < threshold β}
    cond_model_diff -- No --> ending
    cond_model_diff -- Yes --> noti

    noti -- Admin take action --> cond_new_feature{Use current or new features?}

    cond_new_feature -- New --> train_new[Train new feature model offline]
    cond_new_feature -- Current --> chal_model
    chal_model -->replace[Replace old model]
    train_new --> new_pipe[Deploy new data pipeline]
    new_pipe --> replace
    
    replace --> keep_model[Keep top models for N months]
    keep_model --> ending

```
**Design principles:**  
- For the current features used, the model will be shadowing regulary trained. To make sure, we always have a better model standing by.
- The model retention period or number can be configurable, to make sure, we can recover from a previous model version, if needed.
- All change decisions are made by human.

**Note that:** Any feature change will impact both model and feature preparation.

## Flows
Here we show the sequential diagrams of the evaluation pipeline:

```mermaid
sequenceDiagram
    participant EV as Evaluation Pipeline
    participant TRN as Training Pipeline
    participant TXN as PP TXN
    participant MDL as Model Repo
    participant PDR as Predicted Result
    participant CFR as Answer from CFR
    participant FT as Feature Store
    participant DB as Eval DB

    TRN->>TRN: regulary train new challenger models
    TRN->>MDL: save challenger models <br> and their corresponse data set to repo

    note over EV,MDL: check statistical diff

    EV->>TXN: get PP model trained data <br> and up-to-date data
    activate EV
    activate TXN
    TXN-->>EV: PP transaction data
    deactivate TXN
    EV->>EV: check statistical diff
    EV->>DB: save statistical diff

    alt diff > threshold
        EV->>EV: notify to admin <br> (to maintain model performance and features)
        EV->>EV: check model performance drop (below section)
        deactivate EV
    end

    note over EV,CFR: check model performance drop
    
    EV->>PDR: get historical predicted result of the current model
    activate EV
    activate PDR
    PDR-->>EV: predicted result
    deactivate PDR
    EV->>CFR: get actual answer from CFR
    activate CFR
    CFR-->>EV: actual answer
    deactivate CFR
    EV->>EV: check model performance drop
    EV->>DB: save model performance
    
    alt drop > threshold
        EV->>MDL: get best challenger model
        activate MDL
        MDL-->>EV: challenger model
        deactivate MDL
        EV->>FT: get feature snapshot of the current model predicted
        activate FT
        FT-->>EV: feature snapshot
        deactivate FT
        EV->>EV: try these features with the challenger model, <br> then compare performance with the current model
        EV->>EV: notify admin <br> (to know the drop <br> or deploy new model)
        deactivate EV
    end
```
> ⚠️ As of 2025, actual answer from CFR is delay around 21 days to complete for the *invesment fraud* cases, and 3 days for others.

## Apache Airflow pipelines
TODO detail of the Airflow

## Data Prep workers
These are data preparation workers saving data to SeaweedFS for evaluation pipeline.

- PromptPay Transaction Recorder. [Detail](../data-prep.md#promptpay-transaction-recorder)
- Predicted Score Capture. [Detail](../data-prep.md#predicted-score-capture)
- CFR Data Capture. [Detail](../data-prep.md#cfr-data-capture)