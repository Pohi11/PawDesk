# Spec Delta

## ADDED Requirements

### Requirement: Model calls can offer tools
A model call SHALL accept a list of tools, each with a name, description, and JSON schema for its arguments. When the model requests tool calls, the result SHALL return each call's id, tool name, and raw argument text, plus the assistant message to append to the conversation. The model span SHALL record the requested calls. A call that offers tools SHALL ask the provider to route only to endpoints that support every requested parameter.

#### Scenario: Model requests a tool
- **WHEN** a call offers a tool and the model answers with a call to it
- **THEN** the result contains the call's id, name, and arguments, and the span output lists the call

#### Scenario: Tools require supporting endpoints
- **WHEN** a model call offers tools
- **THEN** the request body asks the provider to require support for all requested parameters
