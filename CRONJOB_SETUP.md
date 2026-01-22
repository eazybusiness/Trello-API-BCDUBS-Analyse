# Automated Report Generation with Cronjob

This guide explains how to set up automated report generation that runs every 15 minutes and optionally uploads reports to your hosting provider via SSH.

## Quick Setup

### 1. Test the Script Locally

First, test that the script works correctly:

```bash
cd /home/nop/CascadeProjects/trello_api
./generate_all_reports.sh
```

Check the log file:
```bash
cat reports/generation.log
```

### 2. Configure SSH Upload (Optional)

If you want to automatically upload reports to your hosting provider, configure the IONOS connection in your `.env` file.

Edit `.env` (it is already gitignored):

```bash
vim .env
```

Add these variables:

```bash
IONOS_SSH=user@host
IONOS_SSH_PW=your_password
IONOS_PATH=/freelancer/dubbing
```

Notes:
- `IONOS_SSH` supports `user@host` or `user@host:port`.
- Upload runs automatically on each execution of `generate_all_reports.sh`.
- To disable upload for a run: `./generate_all_reports.sh --no-upload`

### 3. Set Up Cronjob

Open crontab editor:
```bash
crontab -e
```

Add this line to run every 15 minutes:
```bash
*/15 * * * * /home/nop/CascadeProjects/trello_api/generate_all_reports.sh >> /home/nop/CascadeProjects/trello_api/reports/cron.log 2>&1
```

Or with upload enabled:
```bash
*/15 * * * * /home/nop/CascadeProjects/trello_api/generate_all_reports.sh >> /home/nop/CascadeProjects/trello_api/reports/cron.log 2>&1
```

### 4. Verify Cronjob is Running

Check if cronjob is registered:
```bash
crontab -l
```

Wait 15 minutes and check the logs:
```bash
tail -f /home/nop/CascadeProjects/trello_api/reports/cron.log
```

## Alternative Cronjob Schedules

```bash
# Every 30 minutes
*/30 * * * * /path/to/generate_all_reports.sh

# Every hour
0 * * * * /path/to/generate_all_reports.sh

# Every 6 hours
0 */6 * * * /path/to/generate_all_reports.sh

# Once per day at 8:00 AM
0 8 * * * /path/to/generate_all_reports.sh

# Every weekday at 9:00 AM
0 9 * * 1-5 /path/to/generate_all_reports.sh
```

## SSH Key Setup (for passwordless upload)

If you don't have SSH keys set up:

```bash
# Generate SSH key
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# Copy public key to remote server
ssh-copy-id your-username@your-server.com

# Test connection
ssh your-username@your-server.com
```

## Troubleshooting

### Check if cronjob is running
```bash
grep CRON /var/log/syslog | tail -20
```

### Check script logs
```bash
cat reports/generation.log
cat reports/cron.log
```

### Test script manually
```bash
cd /home/nop/CascadeProjects/trello_api
./generate_all_reports.sh
echo $?  # Should output 0 if successful
```

### Common Issues

1. **Permission denied**: Make sure script is executable
   ```bash
   chmod +x generate_all_reports.sh
   ```

2. **Virtual environment not found**: Check venv path in script
   ```bash
   ls -la venv/bin/activate
   ```

3. **SSH upload fails**: Test SSH connection manually
   ```bash
   ssh your-username@your-server.com
   ```

4. **Python errors**: Check if all dependencies are installed
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## What the Script Does

1. Activates Python virtual environment
2. Fetches latest data from Trello API
3. Generates Speaker Workload HTML report
4. Generates Completed Projects HTML report
5. (Optional) Uploads reports to remote server via SSH
6. Logs all activities to `reports/generation.log`

## File Locations

- **Script**: `/home/nop/CascadeProjects/trello_api/generate_all_reports.sh`
- **Reports**: `/home/nop/CascadeProjects/trello_api/reports/`
- **Logs**: `/home/nop/CascadeProjects/trello_api/reports/generation.log`
- **Cronjob log**: `/home/nop/CascadeProjects/trello_api/reports/cron.log`

## Security Notes

- Keep your `.env` file secure (already in .gitignore)
- Use SSH keys instead of passwords for remote upload
- Restrict permissions on SSH keys: `chmod 600 ~/.ssh/id_rsa`
- Consider using a dedicated user for cronjobs
- Regularly review logs for any issues

## Monitoring

Set up email notifications for cronjob failures:

```bash
# Add MAILTO at the top of crontab
MAILTO=your-email@example.com

# Cronjob will email you if it fails
*/15 * * * * /path/to/generate_all_reports.sh
```

## Manual Report Generation

You can always generate reports manually:

```bash
cd /home/nop/CascadeProjects/trello_api
source venv/bin/activate

# Generate all reports
python3 trello_client.py
python3 generate_html_report.py
python3 generate_completed_html.py
```
