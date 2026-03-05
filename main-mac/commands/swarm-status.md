Check the health and status of both helper machines.

## Instructions

1. Run the health check script:
   ```bash
   bash ~/.device-link/shared/healthcheck.sh
   ```
2. Display the results in a clear summary
3. If any helper is offline or degraded, suggest troubleshooting steps:
   - Check Tailscale: `tailscale status`
   - Try SSH directly: `ssh helper-left` or `ssh helper-right`
   - Check tmux on the helper: `tmux ls`
   - Restart the brain: `./left-brain/start.sh` or `./right-brain/start.sh`
