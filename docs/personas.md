# Personas

## Persona 1: Application Support Analyst

This user supports diagnostic imaging workflows and receives operational tickets from clinical or technical users.

### Pain Points

- Needs to check multiple systems manually.
- Does not have one view of accession state.
- May not know which message failed.
- Needs to determine whether the issue is RIS, PACS, reporting, or downstream-related.
- Needs to explain the issue clearly to another team or vendor.

### What They Need

- Accession search
- Current state comparison across systems
- Event history
- Incident list
- Failed message view
- Recommended next action

## Persona 2: Platform / Cloud / DevOps Engineer

This user cares about reliability, failure handling, observability, and deployment.

### Pain Points

- Message processing may fail silently.
- Retry and dead-letter handling may not be obvious.
- Operational metrics may be missing.
- Deployments may not be repeatable.

### What They Need

- SQS decoupling
- DLQ handling
- CloudWatch metrics and alarms
- Terraform-managed infrastructure
- CI/CD workflow
- cost controls

## Persona 3: Solutions Architect / Technical Consultant

This user cares about business value, tradeoffs, stakeholder communication, and system design.

### Pain Points

- Technical solutions may not connect clearly to real operational problems.
- Stakeholders may not understand why architecture decisions matter.
- Compliance and privacy boundaries must be handled carefully.

### What They Need

- Clear problem statement
- Architecture diagram
- Before/after workflow
- Tradeoff explanation
- Security and privacy boundaries
- Demo story that connects technology to business value
