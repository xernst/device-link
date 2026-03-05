Send an analytical task to the LEFT BRAIN helper machine.

The left brain specializes in: code review, testing, debugging, security analysis, linting, type checking, performance profiling, and refactoring.

## Instructions

1. Take the user's task from $ARGUMENTS
2. Run the trigger script to send it to the left brain:
   ```bash
   bash ~/.device-link/trigger/trigger.sh left "$ARGUMENTS"
   ```
3. Wait for the result and display it to the user
4. If the left brain is unreachable, suggest checking `device-link status`
