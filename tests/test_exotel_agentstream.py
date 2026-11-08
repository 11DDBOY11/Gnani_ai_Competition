import asyncio
import base64
import json

from app.server import ExotelAgentStream


class FakeWebSocket:
    def __init__(self, events):
        self.events = iter(events)
        self.sent = []

    async def receive(self):
        return next(self.events)

    async def send_json(self, event):
        self.sent.append(event)

    async def close(self, code=1000, reason=""):
        self.closed = (code, reason)


def _text(event):
    return {"type": "websocket.receive", "text": json.dumps(event)}


def test_exotel_agentstream_maps_media_and_mark_to_call_pcm_and_ack():
    pcm = b"\x01\x00" * 1600
    incoming = [
        _text({"event": "connected"}),
        _text({"event": "start", "stream_sid": "MZ-stream", "start": {
            "stream_sid": "MZ-stream", "call_sid": "CA-call",
            "media_format": {"encoding": "audio/x-raw", "sample_rate": "8000", "bit_rate": "16"},
        }}),
        _text({"event": "media", "stream_sid": "MZ-stream", "media": {
            "payload": base64.b64encode(pcm).decode("ascii"),
        }}),
        _text({"event": "mark", "stream_sid": "MZ-stream", "mark": {"name": "response-1"}}),
    ]

    async def run():
        socket = FakeWebSocket(incoming)
        adapter = ExotelAgentStream(socket)
        await adapter.wait_for_start()
        assert adapter.call_sid == "CA-call"
        await adapter.send_json({"type": "atomic_reply", "response_id": "response-1", "text": "hello"})
        await adapter.send_bytes(pcm)
        media = [event for event in socket.sent if event["event"] == "media"]
        assert len(media) == 1
        assert base64.b64decode(media[0]["media"]["payload"]) == pcm
        assert socket.sent[-1] == {
            "event": "mark", "stream_sid": "MZ-stream", "mark": {"name": "response-1"},
        }
        received_audio = await adapter.receive()
        assert received_audio["bytes"] == pcm
        received_mark = await adapter.receive()
        assert json.loads(received_mark["text"]) == {
            "type": "playback_done", "response_id": "response-1",
        }

    asyncio.run(run())
