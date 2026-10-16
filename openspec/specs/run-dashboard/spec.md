# run-dashboard Specification

## Purpose
The operator dashboard: watch a run live as a graph and a timeline, inspect any span, decide flagged requests, follow cost, latency, and eval results, and submit demo requests. It is served without exposing the backend to the browser.

## Requirements

### Requirement: The run graph shows each step's status and kind
The run view SHALL draw the workflow as a graph:
- **Nodes:** intake, records, compliance, capacity, route, resolver, reply, review, and send.
- **Status:** each node SHALL show `waiting`, `running`, `ok`, `error`, or `skipped`, derived from the request's spans and state.
- **Kind:** each node SHALL be colored by its kind (model, code, tool, or human).

#### Scenario: Parallel steps running
- **WHEN** the intake and records spans are both running
- **THEN** both nodes show `running`

#### Scenario: Skipped resolver
- **WHEN** a request was routed straight to drafting
- **THEN** the resolver node shows `skipped`

#### Scenario: Waiting for review
- **WHEN** a request is in `needs_review`
- **THEN** the review node shows `running` and the send node shows `waiting`

### Requirement: The timeline shows overlapping steps
The timeline SHALL place every span of a trace as a bar positioned by its start and end relative to the trace's first span, indented by its depth in the span tree. A span still running SHALL extend to the current time.

#### Scenario: Concurrent spans overlap
- **WHEN** intake ran from 0.1 s to 4.6 s and records from 0.2 s to 3.0 s
- **THEN** their bars overlap on the timeline

#### Scenario: Nesting
- **WHEN** a model span is a child of the intake span
- **THEN** it is drawn one level deeper than the intake span

### Requirement: The backend is reached only through an allowlisted proxy
The browser SHALL reach the backend only through the dashboard's own route. The route SHALL forward only these paths:
- `GET` for requests, reviews, metrics, evals, demo samples, generated demo requests, and demo certificate images;
- `POST` for staff actions and demo submissions.

Everything else SHALL be refused with 404. The backend address SHALL NOT appear in browser code.

#### Scenario: Allowed path
- **WHEN** the browser asks for `GET /api/requests/<id>/events`
- **THEN** the route forwards it and streams the response through

#### Scenario: Refused path
- **WHEN** the browser asks for `GET /api/health/db` or `DELETE /api/requests/<id>`
- **THEN** the route answers 404 without contacting the backend

#### Scenario: Certificate images pass through
- **WHEN** the browser asks for `GET /api/demo/generated/42/certificate.png`
- **THEN** the route forwards it and returns the image unchanged

#### Scenario: No backend address in client code
- **WHEN** the client components are checked
- **THEN** none of them reads the backend address

### Requirement: Operators can review, measure, and demo from the dashboard
The dashboard SHALL provide:
- a requests list page linking each request to its run view;
- a review queue page showing each waiting request's flag reasons and draft, with approve, edit and approve, and reject (with a reason);
- a metrics page charting cost per step, flag rate, and run duration;
- an evals page listing every report;
- a Try panel on the home page that submits a sample and opens its live run view.

#### Scenario: Span inspector formatting
- **WHEN** a model span with tokens, cost, and latency is selected
- **THEN** the inspector shows its tokens, its cost in dollars, and its duration in seconds

#### Scenario: Demo opens the live view
- **WHEN** a sample is submitted from the Try panel
- **THEN** the browser navigates to that request's live run view

### Requirement: The Try page previews a request and its certificate
The Try page SHALL let the visitor generate a random request, and show its message (editable), its scenario in plain words, and its certificate image before sending. A new request can be generated at any time. Each generation SHALL send the pet names generated earlier in this browser session, the latest 10, so the next name is fresh. Fixed samples SHALL show their certificate too, when they have one.

#### Scenario: Generate and preview
- **WHEN** the visitor generates a request
- **THEN** the page shows the generated message, the scenario, and the certificate image for that request's seed

#### Scenario: Send a generated request
- **WHEN** the visitor sends a generated request
- **THEN** it is submitted by its seed, and the browser opens its live run view

#### Scenario: Recent names go with each generation
- **WHEN** the visitor generates a request after generating Juno and Pickle
- **THEN** the page asks for the new request with Juno and Pickle as names to avoid

### Requirement: Path steps explain themselves
Hovering or focusing a step in the run view's path SHALL show a tooltip with what the step does and, once the step has run, a one-line summary of its result for this request. A step that is skipped or has not run SHALL say so. The summary SHALL come only from the request detail already loaded, and SHALL update as the run does.

#### Scenario: A finished step
- **WHEN** the visitor hovers the Compliance step of a request whose Bordetella record expired before the stay
- **THEN** the tooltip says what the compliance check does, and that Bordetella expired

#### Scenario: A step that did not run
- **WHEN** the visitor hovers the Staff review step of a request sent without review
- **THEN** the tooltip says what staff review is for, and that this request did not need it

#### Scenario: Keyboard
- **WHEN** the visitor tabs to a step
- **THEN** the same tooltip is shown and announced as the step's description, Escape hides it, and Enter opens the step in the inspector

### Requirement: The home page introduces PawDesk and holds the Try panel
The home page (`/`) SHALL open with what PawDesk does, why it was built, its main features, and a worked request, then the Try panel. Below the panel it SHALL name each agent with what it reads, what it returns, and what code checks, then explain the steps, the guarantees the tests check, how the code is written, and which technologies serve each skill in the job posting. `/demo` SHALL redirect to `/`, and the requests list SHALL be at `/requests`.

#### Scenario: Opening the home page
- **WHEN** a visitor opens `/`
- **THEN** the page says what PawDesk does and why it was built, shows the worked example, and shows the Try panel's samples and its "Make one up" choice

#### Scenario: The agents
- **WHEN** a visitor reads the agents section
- **THEN** it names the intake, records, resolver, and reply agents, each with what it reads, what it returns, and what code checks

#### Scenario: The old Try page address
- **WHEN** a visitor opens `/demo`
- **THEN** the browser lands on `/`

#### Scenario: The requests list
- **WHEN** a visitor follows the navigation's Requests link
- **THEN** the browser opens `/requests`, which lists the requests

### Requirement: The home page explains the booking rules
The home page SHALL explain the rules code checks: for each service, how long a visit lasts, whether it needs a kennel, and the vaccines dogs and cats need; when a vaccine covers a stay; how a dog's weight sets its kennel size; which dates a request can ask for; and what happens when a rule isn't met. The vaccine lists, weight bands, and booking horizon SHALL match the ones the backend uses.

#### Scenario: Services side by side
- **WHEN** a visitor reads the booking rules
- **THEN** boarding shows at least one night and a kennel, daycare and grooming show a single day and no kennel, and each shows its vaccines for dogs and cats

#### Scenario: The rules match the backend
- **WHEN** the rule data the page reads is compared with the seeded facility's vaccine rules, the size class thresholds, and the booking horizon
- **THEN** they match

### Requirement: Long pages offer a way back to the top
Every dashboard page SHALL show a "Back to top" button once the visitor has scrolled further than one window height, and SHALL hide it again above that point. Pressing the button SHALL scroll the page to the top, smoothly unless the visitor's system asks for reduced motion. While hidden, the button SHALL not be reachable by keyboard or by assistive technology.

#### Scenario: At the top of the page
- **WHEN** a visitor opens a page and has not scrolled
- **THEN** no "Back to top" button is visible or focusable

#### Scenario: Scrolled past the first screen
- **WHEN** a visitor scrolls further than one window height
- **THEN** the "Back to top" button appears in the bottom right corner

#### Scenario: Pressing the button
- **WHEN** a visitor presses "Back to top"
- **THEN** the page scrolls to the top and the button hides

#### Scenario: Reduced motion
- **WHEN** the visitor's system asks for reduced motion and they press "Back to top"
- **THEN** the page jumps to the top without a smooth scroll

### Requirement: Tapping on a touch screen draws no highlight
The dashboard SHALL NOT draw the browser's tap highlight on any element. On a device whose main pointer is a finger, a tapped text field, menu, or radio SHALL NOT draw a focus outline. A visitor who moves focus with the keyboard SHALL still see the focus outline on every control.

#### Scenario: Tapping a button on a phone
- **WHEN** a visitor taps a button on a phone
- **THEN** no tap highlight is drawn over it

#### Scenario: Tapping a text field on a phone
- **WHEN** a visitor taps the request text box on a phone
- **THEN** the text box has focus and no focus outline

#### Scenario: Moving with the keyboard
- **WHEN** a visitor on a desktop presses Tab to reach a control
- **THEN** the control shows the focus outline

### Requirement: The architecture page shows how the system works
The dashboard SHALL have an Architecture page at `/architecture`, linked from the navigation. It SHALL draw the system's parts and their connections, a request's path through the agents and checks, the lifecycle states, the step loop, what a model's output passes before code uses it, and how tracing records each step. Each diagram SHALL have a name and a text equivalent. The page SHALL not scroll sideways at phone width.

#### Scenario: Opening the page from the navigation
- **WHEN** a visitor follows the navigation's Architecture link
- **THEN** the browser opens `/architecture`, which shows the six diagrams by name

#### Scenario: Diagrams in words
- **WHEN** a screen reader reaches a diagram
- **THEN** it announces the diagram's name and a description that names the same parts and connections

#### Scenario: Phone width
- **WHEN** a visitor opens the page 375 pixels wide
- **THEN** the page doesn't scroll sideways, and a wide diagram scrolls inside its own frame

### Requirement: The architecture page's lifecycle matches the backend
The lifecycle diagram's transitions, the actor allowed on each, and the states that can fail SHALL match the backend's lifecycle rules. The step loop's table SHALL match the orchestrator's map from state to step. Every transition in the page's data SHALL have an arrow in the diagram.

#### Scenario: Transitions match the lifecycle rules
- **WHEN** the page's transitions and failable states are compared with the backend's allowed transitions and failable states
- **THEN** they match

#### Scenario: Steps match the orchestrator
- **WHEN** the page's state-to-step table is compared with the orchestrator's step map
- **THEN** each state names the same step function

#### Scenario: Every transition is drawn
- **WHEN** the page's transitions are compared with the arrows the diagram draws
- **THEN** each transition has exactly one arrow, and each arrow is a transition

### Requirement: The navigation links to the source code and the portfolio
The navigation bar on every page SHALL end with a "Source code" link to https://github.com/Pohi11/PawDesk and a "Portfolio" link to https://pohi.me/. Both SHALL open in a new tab without giving the new page access to the dashboard's window, and each SHALL tell assistive technology that it opens a new tab.

#### Scenario: Source code link
- **WHEN** a visitor looks at the navigation bar
- **THEN** a "Source code" link points to https://github.com/Pohi11/PawDesk and opens in a new tab

#### Scenario: Portfolio link
- **WHEN** a visitor looks at the navigation bar
- **THEN** a "Portfolio" link points to https://pohi.me/ and opens in a new tab

### Requirement: The worked example shows the attached vaccine card
The home page's worked example SHALL be labeled as an example. It SHALL show the vaccine card image the clean sample sends, between the pet parent's message and the facts code checked, marked as input a model read. The card SHALL first show as a short preview that a visitor can expand to the full card and collapse again.

#### Scenario: The card in the worked example
- **WHEN** a visitor opens `/`
- **THEN** the worked example shows Biscuit's vaccine card image, and the image loads

#### Scenario: The example is labeled
- **WHEN** a visitor opens `/`
- **THEN** the worked example's first line says it is an example request

#### Scenario: Expanding the card
- **WHEN** a visitor expands the card in the worked example
- **THEN** the full card shows, and the control says it will collapse the card

### Requirement: The hero's How it works link opens the booking rules
The home page's "How it works" link SHALL scroll the page to the booking rules section, the first section of the explanation.

#### Scenario: Following How it works
- **WHEN** a visitor on `/` follows the "How it works" link
- **THEN** the page scrolls to the booking rules section and its heading is in view

### Requirement: The coverage diagram is a hypothetical example
The booking rules' coverage diagram SHALL describe a hypothetical dog's stay, not a pet on file, because its expiry dates are chosen to show one shot that covers the stay and one that expires during it.

#### Scenario: The diagram's subject
- **WHEN** a visitor reads the coverage diagram in the booking rules
- **THEN** it is labeled as a hypothetical dog's stay, and it still shows one shot that covers the stay and one that expires during it

### Requirement: Every Try preview opens with a summary
Every preview on the Try page, of a sample or a generated request, SHALL open with the same summary: the pet, service, and dates, then the owner, the pet's breed and weight when known, and what the vaccine card shows. The page SHALL open with "Make one up" selected and a generated request in the preview. Making up that opening request SHALL NOT change the visitor's choice. Choosing "Make one up" SHALL show the request already made up; only "Make another" or a page load SHALL make up a new one.

#### Scenario: Opens on Make one up
- **WHEN** the visitor opens the Try page
- **THEN** "Make one up" is selected and the preview shows a generated request

#### Scenario: A sample's summary
- **WHEN** the visitor chooses the clean boarding sample
- **THEN** the preview opens with Biscuit, boarding, and the dates, then the owner, breed, weight, and that every vaccine on the card is current

#### Scenario: A sample chosen while the opening request is made up
- **WHEN** the visitor chooses the clean boarding sample before the opening generated request has arrived, and then sends
- **THEN** the clean sample stays chosen after the generated request arrives, and the clean sample is the request sent

#### Scenario: Going back to Make one up keeps the request
- **WHEN** the visitor chooses a sample and then chooses "Make one up" again
- **THEN** the preview shows the same generated request as before, and no new one is made up

#### Scenario: Make another makes a new request
- **WHEN** the visitor clicks "Make another"
- **THEN** a new generated request is made up

### Requirement: The worked example shows what PawDesk did
The worked example SHALL end with the outcome of the clean sample's run: that it booked a medium kennel for the stay and sent the reply with no one on staff involved, then the reply's subject and first paragraph. The rest of the reply SHALL open on demand. The reply SHALL be the one the clean sample's recorded run sends.

#### Scenario: The outcome
- **WHEN** a visitor opens `/`
- **THEN** the worked example says a medium kennel was booked, shows the Sent tag, and shows the reply's subject and first paragraph

#### Scenario: The full reply
- **WHEN** a visitor opens the rest of the reply
- **THEN** the whole reply shows, ending with its sign-off

#### Scenario: The quoted reply is the real one
- **WHEN** the clean sample runs on its recorded responses
- **THEN** the reply it sends has the same subject and first paragraph as the worked example
