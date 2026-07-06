#!/usr/bin/python3
"""Small local-only HTTP CONNECT proxy for routing HTTPS traffic through this host."""

import asyncio
import contextlib
import signal


HOST = "127.0.0.1"
PORT = 3128
BUFFER_SIZE = 64 * 1024


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(BUFFER_SIZE):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        with contextlib.suppress(Exception):
            writer.close()


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=10)
        if not request_line:
            writer.close()
            return

        parts = request_line.decode("latin1").strip().split()
        if len(parts) < 3 or parts[0].upper() != "CONNECT":
            writer.write(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        target = parts[1]
        if ":" not in target:
            writer.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        host, port_text = target.rsplit(":", 1)
        port = int(port_text)
        if port != 443:
            writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        while True:
            header_line = await reader.readline()
            if header_line in (b"\r\n", b"\n", b""):
                break

        upstream_reader, upstream_writer = await asyncio.open_connection(host, port)
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()

        await asyncio.gather(
            pipe(reader, upstream_writer),
            pipe(upstream_reader, writer),
        )
    except Exception:
        with contextlib.suppress(Exception):
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            await writer.drain()
        writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle_client, HOST, PORT)
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    async with server:
        await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(main())
