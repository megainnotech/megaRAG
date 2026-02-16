# Fraud Engine Versioning Control

PromptGuard is designed to self maintaining in term of model performance.
It will periodically evaluate and update prediction models, and also serving the risk score. This section show how we control these modules versioning control.

## TODO
...  

* Update new model, existing features
* Upgrade new model and NEW features
  * relevant components
* we need no downtime for updrading a model
* rolling update strategy
  * how long we need for blue/green switch?
  * Adhoc sizing for upgrade model 
  * 