# Spec Delta

## Purpose

Keeps the dashboard's user-facing text plain and accurate. A shared rule list defines what the build can check by itself. Sentences that report a decision name who made it.

## ADDED Requirements

### Requirement: Dashboard text contains no banned words or phrases
The dashboard's user-facing text SHALL contain no word or phrase from the shared banned list, matched as whole words regardless of case. User-facing text means rendered text and string values in the dashboard's source. Style class names, import paths, comments, and test files are not user-facing text.

#### Scenario: A banned word in rendered text
- **WHEN** a page's rendered text contains "simply"
- **THEN** the copy check fails and names the file, the line, and the word

#### Scenario: Class names are not text
- **WHEN** an element's style classes include `justify-self-end`
- **THEN** the copy check does not report it

#### Scenario: The current dashboard passes
- **WHEN** the copy check runs on the dashboard source
- **THEN** it reports nothing

### Requirement: Dashboard text uses no em dash inside a sentence
The dashboard's user-facing text SHALL NOT contain an em dash, except a string that is only an em dash, which marks a missing value in a table or figure.

#### Scenario: An em dash inside a sentence
- **WHEN** a label reads "Costs — as reported"
- **THEN** the copy check fails and names the file and the line

#### Scenario: A missing-value placeholder
- **WHEN** a figure with no value shows "—"
- **THEN** the copy check does not report it

### Requirement: Demo sample descriptions follow the same rules
The title and description of every demo sample the backend serves SHALL pass the same banned list and em-dash rule as the dashboard, read from the same shared list.

#### Scenario: Samples pass
- **WHEN** every demo sample's title and description are checked
- **THEN** none contains a banned word, a banned phrase, or an em dash

#### Scenario: One list for both checks
- **WHEN** a word is added to the shared banned list
- **THEN** both the dashboard check and the sample check reject it

### Requirement: Outcome sentences name who decided
The sentence that states a request's outcome SHALL name who decided it. A request sent without review SHALL say the checks decided it. A staff decision SHALL start with the staff member's name.

#### Scenario: Sent without review
- **WHEN** a request was sent with no staff approval
- **THEN** the outcome sentence says the checks passed it and no person was needed

#### Scenario: Declined by staff
- **WHEN** Sam declined a request
- **THEN** the outcome sentence starts with "Sam declined"

#### Scenario: Edited by staff
- **WHEN** Dana edited the reply and sent it
- **THEN** the outcome sentence starts with "Dana edited"

### Requirement: Failure sentences name the step in plain words
The outcome sentence for a failed request SHALL name the step that failed in plain words and SHALL NOT show a raw state name.

#### Scenario: Failed while sending
- **WHEN** a request failed after staff approved it
- **THEN** the outcome sentence says it stopped while sending the reply, and does not contain "approved" as a step name

#### Scenario: Failed while reading
- **WHEN** a request failed during extraction
- **THEN** the outcome sentence says it stopped while reading the request
