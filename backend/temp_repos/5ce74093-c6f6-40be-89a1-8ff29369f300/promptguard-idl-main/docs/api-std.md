# API services standard

## Timeout and Retry Mechanism
### Timeout Policy
An API request is considered timed out if no response is received within 60 seconds.

### Retry Mechanism
- If a timeout occurs, the system will automatically retry the request up to 3 times.
- Each retry attempt will be made after a fixed delay of 3 seconds, measured from the previous attempt (not cumulative or exponential).
- If all three retry attempts fail, the request is considered failed, and appropriate error handling will be triggered.

| Action  | Scenario | Timeout waiting | Delay before attemp |
|---|---|---|---|
| Actual call | Immidiate call API service | 60 sec | + Delay 3 second |
| 1st retry | 1st retry call service | 60 sec | + Delay 3 second |
| 2nd retry | 2nd retry call service | 60 sec | + Delay 3 second |
| 3rd retry | 3rd retry call service | 60 sec | - |
| Error monitor trigger | 3rd retry failed, error handling will be triggered. | -   | - |