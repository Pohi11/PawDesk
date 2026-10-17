# Spec Delta

## ADDED Requirements

### Requirement: Samples end as promised from seeded and printed records
For each fixed sample with a pet on file and a card, the vaccine check and the kennel search SHALL give the outcome the sample promises when run on the freshly seeded data with the dates printed on its card, processed as of the demo day. Without any model, the clean and injection samples SHALL be compliant with a kennel found. The expired-vaccine sample SHALL fail only on Bordetella, with a kennel found.

#### Scenario: Clean sample passes on its records
- **WHEN** the seeded records on file for Biscuit and the dates printed on Biscuit's card are checked for boarding Mar 24 to Mar 27, 2027
- **THEN** the vaccine check is compliant and a medium kennel is found

#### Scenario: Injection sample passes on its records
- **WHEN** the seeded records on file for Pepper and the dates printed on Pepper's card are checked for boarding Mar 24 to Mar 27, 2027
- **THEN** the vaccine check is compliant and a kennel is found

#### Scenario: Expired-vaccine sample fails only on Bordetella
- **WHEN** the seeded records on file for Moose and the dates printed on Moose's card are checked for boarding Mar 10 to Mar 13, 2027
- **THEN** Bordetella is expired, every other required vaccine is ok, and a large kennel is found

#### Scenario: Clean sample does not hang on the card read
- **WHEN** only the seeded records on file for Biscuit are checked for boarding Mar 24 to Mar 27, 2027
- **THEN** the vaccine check is compliant
