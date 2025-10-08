# Plan Then Execute

This command helps plan and execute complex development tasks using a structured, phased approach with living documentation.

## Usage
```
/plan-then-execute [issue-id] [issue description]
```

Examples:
- `/plan-then-execute PRO-123`
- `/plan-then-execute fix the data loader`
- `/plan-then-execute PRO-123 fix the data loader`

## Process Overview

This command guides you through a multi-phase planning and execution workflow:

**Planning Mode** (Steps 1-4):
1. **Issue Discovery**: Retrieve Linear issue or use provided description
2. **Context Gathering**: Review existing documentation and create issue folder
3. **Strategic Planning**: Develop multi-phase implementation strategy
4. **Documentation**: Create living implementation plan

**Execution Mode** (Step 5):
5. **Phased Execution**: Execute ONLY when user explicitly requests (e.g., "execute phase 1" or "execute stage 1A")

## Detailed Workflow

### PLANNING MODE (No Implementation)

The following steps are purely planning - no code implementation occurs:

### Step 1: Issue Discovery and Setup

First, determine if the first argument is a Linear issue ID (e.g., PRO-123) or a task description:

- **If Linear issue**: Use Linear MCP to fetch issue details, description, and comments
- **If description**: Use the provided description as the issue context

Then:
- Check for existing issue folder at `@docs/issues/<issue-name>` (lowercase preferred)
- Create the folder if it doesn't exist
- Download and analyze any attached files or images from Linear
- Follow and summarize any relevant links from Linear (ignore GitHub issue links as these would be redundant)

**Important**: Do NOT search git history or grep the codebase at this stage. Only review:
- The Linear issue (if applicable)
- The contents of the issue folder (if it exists)

### Step 2: Context Summary and User Input

Quickly provide the user with:
- What you found (or didn't find) in Linear
- What documentation exists in the issue folder
- Your current understanding of the problem (which may be minimal)

**If information is sparse or missing**, immediately ask the user to describe:
- The problem to be solved
- Key requirements or constraints
- Any relevant context

This ensures time isn't wasted searching when the user can provide the context directly.

### Step 3: Strategic Planning

Based on the context from Linear/issue folder AND the user's description, analyze the requirements and propose:
- A high-level multi-phase strategy
- Phase breakdown with clear objectives
- Success criteria for each phase
- Testing strategy overview

**Key principle**: This is planning, not implementing yet. Each phase should be sized for 1-2 commits and a single PR.

### Step 4: Create Implementation Plan

Once the user is satisfied with the strategy, create `@docs/issues/<issue-name>/IMPLEMENTATION_PLAN.md` containing:

```markdown
# Implementation Plan: [Issue Title]

## Overview
[Problem statement and solution approach]

## Process Workflow
This project follows the plan-then-execute cycle:
1. Create detailed phase plan (PHASE_X_DETAILED.md)
2. Ask clarifying questions before execution
3. Wait for user to say "execute phase X" or "execute stage XY"
4. Execute the phase/stage
5. Perform criterion-by-criterion self-evaluation
6. User reviews and commits
7. Return to step 1 for next phase

Remember: No staging files unless asked. No execution without explicit request.

## Phases

### Phase 1: [Title]
**Objective**: [Clear goal]
**Success Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2

**Testing Strategy**:
- Unit tests for...
- Integration tests for...

### Phase 2: [Title]
[Similar structure]

## Technical Considerations
[Architecture decisions, dependencies, risks]

## Progress Tracking
[Updated as we complete stages]
```

**Important**: This document serves as your memory bank. Refer back to it frequently, especially the Process Workflow section, to stay on track.

### PHASE-BY-PHASE EXECUTION CYCLE

**Important**: The following steps (5-9) form a repeating cycle that continues until all phases are complete.

### Step 5: Detailed Phase Planning (MANDATORY)

Before ANY phase can be executed, create a detailed plan:

1. **Create Phase Document**: `PHASE_X_DETAILED.md` for the current phase
2. **Detail All Work**: Include:
   - Specific implementation steps
   - File changes required
   - API endpoints/functions to create/modify
   - UI components (if applicable)
   - Test cases to write
   - Integration points
   - Success criteria (detailed)

3. **Assess Phase Size**:
   - If phase fits in 1-2 commits: No stages needed
   - If phase exceeds 1-2 commits: Break into stages (1A, 1B, etc.)

4. **Stage Planning** (if needed):
   - Each stage ends with: tests written → all tests pass → user commits → PR
   - Clearly define stage boundaries

**Important**: Every phase (whether divided into stages or not) must end with: tests written → all tests pass → user commits → PR. This is the natural boundary of any unit of work. Do NOT stage files unless explicitly asked - the user uses unstaged files as their review queue.

This detailed planning happens for EACH phase before it can be executed.

### EXECUTION MODE (Only When Explicitly Requested)

**Important**: No execution happens unless the user explicitly says "execute" followed by a specific phase or stage (e.g., "execute phase 1" or "execute stage 1A").

### Step 6: Pre-Execution Questions (MANDATORY)

Before executing any phase or stage, ALWAYS:
- Review the plan and context
- Ask clarifying questions about:
  - Technical approach
  - UI/UX requirements
  - Integration points
  - Testing expectations
  - Any ambiguities in the plan
- Update planning documents based on the user's answers
- Confirm readiness to proceed

**You must insist on this question phase before any execution.**

### Step 7: Stage Execution (User-Initiated Only)

Only when the user says "execute [phase/stage]":
1. **Pre-Execute**: Ensure questions have been asked and answered
2. **Execute**: Implement the specified phase/stage following the plan
3. **Document Progress**: Immediately update the plan document with what was implemented

### Step 8: Mandatory Self-Evaluation

After ANY execution, ALWAYS:
1. **Present Evaluation**: Go through each success criterion one by one
2. **Check Completeness**: Explicitly state whether each criterion was met, partially met, or not met
3. **Identify Gaps**: List any missing functionality, tests, or requirements
4. **Update Documentation**: Record the evaluation results in the plan

**Important**: Do NOT consider a stage complete until you've provided this criterion-by-criterion evaluation and the user has reviewed it. This often reveals missing pieces that seemed complete at first glance.

### Step 9: Phase/Stage Completion and Iteration

After completing a phase or stage:
1. **Update Progress**: Mark phase/stage as complete in documentation
2. **Review Overall Progress**: Check against project goals
3. **Next Phase Planning**: Return to Step 5 for the next phase
4. **Repeat**: Continue Steps 5-9 until the entire project is complete

**Important**: This creates a continuous loop where after EVERY phase completion, you must:
- Create a new `PHASE_X_DETAILED.md` for the next phase (Step 5)
- Ask pre-execution questions (Step 6)
- Wait for "execute" command (Step 7)
- Perform self-evaluation (Step 8)
- Then return here to Step 9

Continue this cycle until all phases in the IMPLEMENTATION_PLAN.md are complete.
After evaluation, update the plan document with:
- What was accomplished (detailed list)
- Evaluation results for each criterion
- Lessons learned
- Any adjustments to upcoming stages
- Current state for context window recovery

**Critical**: The plan document must be updated immediately after each planning decision and execution step to survive context window compaction.



## Key Success Factors

1. **Living Documentation**: Plans are updated IN REAL-TIME during planning and execution
2. **Small Stages**: Each stage = 1-2 commits max
3. **Questions First**: Surface ambiguities before coding
4. **Mandatory Self-Evaluation**: Separate step to verify completeness against all criteria
5. **Clear Commits**: Strategic staging for easy review
6. **Compaction Resilience**: Documentation always current for context recovery

## Example Folder Structure

```
docs/issues/
└── pro-123/
    ├── IMPLEMENTATION_PLAN.md
    ├── PHASE_1_DETAILED.md
    ├── PHASE_2_DETAILED.md
    ├── PHASE_3_DETAILED.md
    ├── background/
    │   └── requirements.pdf
    ├── mocks/
    │   ├── README.md
    │   └── dashboard.tsx
    └── progress/
        └── phase_1_complete.md
```

## Command Behavior

When the user runs this command, you will:

**Planning Mode:**
1. **Initialize**: Set up issue folder and gather context (Linear + existing docs only)
2. **Summarize**: Present what was found and ask for the user's description if needed
3. **Plan**: Propose strategic approach with phases (each 1-2 commits)
4. **Iterate**: Refine based on user feedback
5. **Document**: Create comprehensive IMPLEMENTATION_PLAN.md
6. **Detail Phase**: Create PHASE_X_DETAILED.md for the first phase

**Execution Mode (User-Initiated):**
7. **Wait**: No execution until the user explicitly requests "execute [phase/stage]"
8. **Question**: ALWAYS ask clarifying questions before execution
9. **Execute**: Implement only the requested phase/stage
10. **Evaluate**: MANDATORY criterion-by-criterion self-evaluation
11. **Complete**: Update documentation and return to step 6 for next phase

This creates a continuous cycle of detailed planning → execution → evaluation for each phase until project completion.
