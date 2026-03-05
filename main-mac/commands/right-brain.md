Send a creative task to the RIGHT BRAIN helper machine.

The right brain specializes in: architecture design, research, documentation, PRDs, UI/UX review, brainstorming, planning, and prototyping.

## Instructions

1. Take the user's task from $ARGUMENTS
2. Run the trigger script to send it to the right brain:
   ```bash
   bash ~/.device-link/trigger/trigger.sh right "$ARGUMENTS"
   ```
3. Wait for the result and display it to the user
4. If the right brain is unreachable, suggest checking `device-link status`
