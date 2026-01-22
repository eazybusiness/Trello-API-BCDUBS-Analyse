import os
import posixpath
import re
import sys
from typing import Tuple

import paramiko
from dotenv import load_dotenv


def _parse_ionos_ssh(value: str) -> Tuple[str, str, int]:
    value = (value or '').strip()
    if not value:
        raise ValueError('IONOS_SSH is empty')

    # Accept: user@host, user@host:port, ssh://user@host:port
    if value.startswith('ssh://'):
        value = value[len('ssh://'):]

    user = None
    host_port = value
    if '@' in value:
        user, host_port = value.split('@', 1)

    host = host_port
    port = 22
    if ':' in host_port:
        host, port_s = host_port.rsplit(':', 1)
        if port_s.isdigit():
            port = int(port_s)
        else:
            host = host_port
            port = 22

    if not user:
        # Common default for IONOS; user should set user@host in IONOS_SSH.
        user = 'sshuser'

    host = host.strip()
    if not host:
        raise ValueError('IONOS_SSH host is empty')

    return user.strip(), host, port


def _ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    remote_dir = remote_dir.rstrip('/')
    if not remote_dir:
        return

    parts = []
    for part in remote_dir.split('/'):
        if not part:
            continue
        parts.append(part)
        p = '/' + '/'.join(parts)
        try:
            sftp.stat(p)
        except IOError:
            sftp.mkdir(p)


def upload_reports() -> int:
    load_dotenv()

    ionos_ssh = os.getenv('IONOS_SSH', '').strip()
    ionos_pw = os.getenv('IONOS_SSH_PW', '').strip()
    ionos_path = os.getenv('IONOS_PATH', '').strip()

    if not ionos_ssh or not ionos_pw or not ionos_path:
        print('Upload skipped: missing IONOS_SSH / IONOS_SSH_PW / IONOS_PATH in .env', file=sys.stderr)
        return 2

    user, host, port = _parse_ionos_ssh(ionos_ssh)

    project_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(project_dir, 'reports')

    files = [
        ('speaker_workload_report.html', os.path.join(reports_dir, 'speaker_workload_report.html')),
        ('completed_projects_report.html', os.path.join(reports_dir, 'completed_projects_report.html')),
    ]

    for _, local_path in files:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f'Missing local report: {local_path}')

    transport = paramiko.Transport((host, port))
    try:
        transport.connect(username=user, password=ionos_pw)
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            remote_dir = ionos_path
            if not remote_dir.startswith('/'):
                remote_dir = '/' + remote_dir

            _ensure_remote_dir(sftp, remote_dir)

            for remote_name, local_path in files:
                remote_path = posixpath.join(remote_dir, remote_name)
                sftp.put(local_path, remote_path)
                print(f'Uploaded {remote_name} -> {host}:{remote_path}', file=sys.stderr)
        finally:
            sftp.close()
    finally:
        transport.close()

    return 0


if __name__ == '__main__':
    try:
        sys.exit(upload_reports())
    except Exception as e:
        print(f'Upload failed: {e}', file=sys.stderr)
        sys.exit(1)
