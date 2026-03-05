Send a task to BOTH helper machines in parallel, then synthesize results.

The left brain will analyze from an analytical perspective (code quality, testing, security).
The right brain will analyze from a creative perspective (architecture, UX, documentation).

## Instructions

1. Take the user's task from $ARGUMENTS
2. Run the trigger script to send it to both brains:
   ```bash
   bash ~/.device-link/trigger/trigger.sh both "$ARGUMENTS"
   ```
3. Wait for both results
4. Synthesize the outputs: combine the left brain's analytical findings with the right brain's creative insights into a unified response
5. Highlight where the two brains agree and where they differ
