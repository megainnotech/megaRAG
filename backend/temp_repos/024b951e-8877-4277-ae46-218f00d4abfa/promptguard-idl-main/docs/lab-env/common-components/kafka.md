# Kafka
Detail…

## Architecture
…

## Config
…

## Topic naming convention
To support Purpose Clarity, Direction, Msg type, Stage, and Auditable, here is the key naming used entire the project: 
* Pattern: `<domain or service>.<message type>.<stage>.[<segment>]`
* Any part can use dash '-' as a word delimeter, e.g., `this-is-a-dataset`

### Example:
* `promptguard.transactionscore.from-pp`
* `promptguard.transactionscore.infered`
