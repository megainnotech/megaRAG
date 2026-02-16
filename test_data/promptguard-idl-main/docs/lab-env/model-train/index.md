# Model Training Pipeline
TODO

## C3 – Component Diagram

![Model Training Pipeline Component Diagram](images/eval-c3.png "Model Training Pipeline Component Diagram")

## Conceptual flow
Below is a conceptual flow of the model training pipeline.
...

Design principles:  
- For the current features used, the model will be shadowing regulary trained. To make sure, we always have a better model standing by.
- The model retention period or number can be configurable, to make sure, we can recover from a previous model version, if needed.
- All change decisions are made by human.

## Flows
Here we show the sequential diagrams of the training pipeline:
...

## Apache Airflow pipelines
TODO detail of the Airflow

## Data Prep workers
These are data prep for training pipeline.
- Predicted result capture
- CFR data capture
- Raw input capture
- 