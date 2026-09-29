"""Encrypted SQLite backup and isolated restore verification."""

import argparse
import datetime
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAGIC = b"HHBACKUP1"


def _save_new(path: Path, data: bytes) -> None:
    if not path.parent.is_dir():
        raise ValueError("Create the protected parent directory first.")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def create_key(private_path: Path, public_path: Path) -> None:
    if private_path.exists() or public_path.exists():
        raise ValueError("A backup key file already exists; refusing to replace it.")
    private_key = x25519.X25519PrivateKey.generate()
    _save_new(private_path, private_key.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    ))
    _save_new(public_path, private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    ))


def _cipher_key(shared_secret: bytes, nonce: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=nonce,
                info=b"harvesthero-sqlite-backup-v1").derive(shared_secret)


def encrypt_backup(source: Path, public_path: Path, output: Path) -> None:
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError("The existing SQLite source database is required.")
    public_key = x25519.X25519PublicKey.from_public_bytes(public_path.read_bytes())
    if not output.parent.is_dir():
        raise ValueError("Create the protected backup destination directory first.")
    with tempfile.TemporaryDirectory(dir=source.parent) as temporary:
        snapshot = Path(temporary) / "inventory.db"
        original = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        try:
            copy = sqlite3.connect(snapshot)
            try:
                original.backup(copy)
            finally:
                copy.close()
        finally:
            original.close()
        ephemeral = x25519.X25519PrivateKey.generate()
        ephemeral_public = ephemeral.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        nonce = os.urandom(12)
        cipher = Cipher(algorithms.AES(_cipher_key(ephemeral.exchange(public_key), nonce)),
                        modes.GCM(nonce)).encryptor()
        cipher.authenticate_additional_data(MAGIC + ephemeral_public)
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with snapshot.open("rb") as data, os.fdopen(descriptor, "wb") as encrypted:
            encrypted.write(MAGIC + ephemeral_public + nonce)
            while chunk := data.read(1024 * 1024):
                encrypted.write(cipher.update(chunk))
            encrypted.write(cipher.finalize())
            encrypted.write(cipher.tag)


def verify_restore(encrypted: Path, private_path: Path) -> dict[str, int]:
    header_size = len(MAGIC) + 32 + 12
    size = encrypted.stat().st_size
    if size < header_size + 16:
        raise ValueError("Not a Harvest Hero encrypted backup.")
    private_key = x25519.X25519PrivateKey.from_private_bytes(private_path.read_bytes())
    with encrypted.open("rb") as source:
        header = source.read(header_size)
        if not header.startswith(MAGIC):
            raise ValueError("Not a Harvest Hero encrypted backup.")
        ephemeral_public = header[len(MAGIC):len(MAGIC) + 32]
        nonce = header[-12:]
        source.seek(size - 16)
        tag = source.read(16)
        source.seek(header_size)
        cipher = Cipher(algorithms.AES(_cipher_key(
            private_key.exchange(x25519.X25519PublicKey.from_public_bytes(ephemeral_public)),
            nonce,
        )), modes.GCM(nonce, tag)).decryptor()
        cipher.authenticate_additional_data(MAGIC + ephemeral_public)
        with tempfile.TemporaryDirectory() as temporary:
            os.chmod(temporary, 0o700)
            restored = Path(temporary) / "inventory.db"
            descriptor = os.open(restored, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as destination:
                remaining = size - header_size - 16
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("Encrypted backup is truncated.")
                    destination.write(cipher.update(chunk))
                    remaining -= len(chunk)
                destination.write(cipher.finalize())
            return _check_restored_database(restored, temporary)


def _check_restored_database(restored: Path, temporary: str) -> dict[str, int]:
    before = sqlite3.connect(f"file:{restored}?mode=ro", uri=True)
    try:
        if before.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed before migration.")
        if before.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Foreign-key validation failed before migration.")
        counts = {}
        for table in ("users", "inventory_items", "pantry_clients", "pantry_visits"):
            counts[table] = before.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        before.close()
    os.environ["HARVESTHERO_DEV_DIR"] = temporary
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from database import Database
    Database(str(restored))
    upgraded = sqlite3.connect(restored)
    try:
        if upgraded.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed after migration.")
        if upgraded.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Foreign-key validation failed after migration.")
        for table, count in counts.items():
            if upgraded.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != count:
                raise ValueError("A core table changed row count during migration.")
        mismatch = upgraded.execute(
            "SELECT COUNT(*) FROM inventory_items item WHERE item.current_quantity != "
            "(SELECT COALESCE(SUM(quantity), 0) FROM item_shelf_stock "
            "WHERE item_id = item.id)"
        ).fetchone()[0]
        if mismatch:
            raise ValueError("Shelf stock does not match catalog quantities.")
    finally:
        upgraded.close()
    return counts


def backup_live(app: str, public_path: Path, private_path: Path, backup_dir: Path,
                run_command=subprocess.run) -> tuple[Path, dict[str, int]]:
    if not public_path.is_file() or not private_path.is_file() or not backup_dir.is_dir():
        raise ValueError("A key pair and existing protected backup directory are required.")
    if backup_dir.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("Encrypted backups must stay outside the repository.")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"daily-{stamp}.hhb"
    output = backup_dir / filename
    if output.exists():
        raise ValueError("A backup with this timestamp already exists; try again later.")
    remote = f"/data/output/backups/{filename}"
    remote_helper = f"/tmp/hh_secure_backup_{stamp}.py"
    remote_public = f"/tmp/hh_backup_{stamp}.pub"

    def invoke(*arguments):
        return run_command(["flyctl", *arguments, "--app", app], check=True,
                           capture_output=True, text=True)

    machines = json.loads(invoke("machine", "list", "--json").stdout)
    if len(machines) != 1:
        raise ValueError("Expected exactly one existing Fly machine; review the app before backing up.")
    if machines[0]["state"] != "started":
        invoke("machine", "start", machines[0]["id"])
    invoke("ssh", "console", "--command",
           "ls -ld /tmp /data/data /data/output/backups /data/data/inventory.db")
    invoke("ssh", "sftp", "put", str(Path(__file__).resolve()),
           remote_helper, "--mode", "0600")
    invoke("ssh", "sftp", "put", str(public_path), remote_public, "--mode", "0600")
    invoke("ssh", "console", "--command",
           f"python {remote_helper} encrypt /data/data/inventory.db "
           f"{remote_public} {remote}")
    invoke("ssh", "sftp", "get", remote, str(output))
    output.chmod(0o600)
    return output, verify_restore(output, private_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    keygen = commands.add_parser("keygen")
    keygen.add_argument("private_key", type=Path)
    keygen.add_argument("public_key", type=Path)
    encrypt = commands.add_parser("encrypt")
    encrypt.add_argument("source", type=Path)
    encrypt.add_argument("public_key", type=Path)
    encrypt.add_argument("output", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("encrypted", type=Path)
    verify.add_argument("private_key", type=Path)
    live = commands.add_parser("backup-live")
    base = Path.home() / "Library" / "Application Support" / "HarvestHero"
    live.add_argument("--app", default="harvest-hero-pantry")
    live.add_argument("--public-key", type=Path, default=base / "backup-keys" / "public.key")
    live.add_argument("--private-key", type=Path, default=base / "backup-keys" / "private.key")
    live.add_argument("--backup-dir", type=Path, default=base / "backups")
    args = parser.parse_args()
    if args.action == "keygen":
        create_key(args.private_key, args.public_key)
        print("Backup key pair created; keep the private key separate from the encrypted backup.")
    elif args.action == "encrypt":
        encrypt_backup(args.source, args.public_key, args.output)
        print("Encrypted SQLite backup created.")
    elif args.action == "backup-live":
        output, counts = backup_live(args.app, args.public_key, args.private_key,
                                     args.backup_dir)
        print(f"Encrypted off-Fly backup restored and verified: {output}")
        print("Row counts:", counts)
        print("Review local and remote ciphertext older than the approved 30-day window; this tool never deletes files.")
    else:
        counts = verify_restore(args.encrypted, args.private_key)
        print("SQLite backup decrypted, integrity-checked, and migrated in an isolated directory.")
        print("Row counts:", counts)


if __name__ == "__main__":
    main()
