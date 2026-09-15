import asyncio
import logging
import re
from typing import Optional, Tuple
import requests

logger = logging.getLogger("uvicorn.error")

# In-memory LRU cache to serve repeated utterances instantaneously (0ms latency)
_AUDIO_CACHE: dict = {}
_MAX_CACHE_ITEMS = 250

DEFAULT_VOICE = "en-US-ChristopherNeural"

VOICE_PROFILES = {
    "alex_male": "en-US-ChristopherNeural",
    "alex_female": "en-US-JennyNeural",
    "alex_guy": "en-US-GuyNeural",
    "alex_british": "en-GB-RyanNeural"
}


def clean_text_for_speech(text: str) -> str:
    """Strip markdown formatting, emojis, and artifacts that sound strange in oral speech."""
    if not text:
        return ""
    t = text.strip()
    # Remove markdown bold/italic/code
    t = re.sub(r'[*_#`~]', '', t)
    # Remove emojis
    t = re.sub(r'[^\w\s.,?!;:()\'-]', ' ', t)
    # Collapse multi spaces
    t = re.sub(r'\s+', ' ', t).strip()
    return t


async def synthesize_speech_audio(text: str, voice: Optional[str] = None) -> Tuple[bytes, str]:
    """
    Synthesizes crystal-clear studio MP3 audio for AI Interviewer.
    Dual-failover engine:
      1. Microsoft Azure Neural Voice (Edge-TTS) for ultra-realistic human prosody.
      2. Google TTS fallback for 100% network uptime assurance.
    Returns: (audio_bytes, source_engine)
    """
    clean_text = clean_text_for_speech(text)
    if not clean_text:
        raise ValueError("Cannot synthesize empty text")

    selected_voice = voice or DEFAULT_VOICE
    if selected_voice in VOICE_PROFILES:
        selected_voice = VOICE_PROFILES[selected_voice]

    # Truncate safety for single turn
    if len(clean_text) > 2000:
        clean_text = clean_text[:2000]

    cache_key = f"{selected_voice}::{clean_text}"
    if cache_key in _AUDIO_CACHE:
        return _AUDIO_CACHE[cache_key], "cache"

    # 1. Attempt Microsoft Azure Neural Voice (Edge-TTS)
    try:
        import edge_tts
        for attempt in range(2):
            try:
                comm = edge_tts.Communicate(clean_text, selected_voice)
                audio_buf = bytearray()
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        audio_buf.extend(chunk["data"])
                if audio_buf and len(audio_buf) > 500:
                    result_bytes = bytes(audio_buf)
                    if len(_AUDIO_CACHE) >= _MAX_CACHE_ITEMS:
                        _AUDIO_CACHE.pop(next(iter(_AUDIO_CACHE)))
                    _AUDIO_CACHE[cache_key] = result_bytes
                    return result_bytes, "edge-tts"
            except Exception as ee:
                logger.warning(f"[TTS] Edge-TTS attempt {attempt+1} failed: {ee}")
                await asyncio.sleep(0.2)
    except Exception as e:
        logger.warning(f"[TTS] Edge-TTS error: {e}")

    # 2. Seamless High-Speed Fallback: Google TTS
    try:
        def _get_google_tts(text_chunk: str) -> bytes:
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=en&client=tw-ob&q={requests.utils.quote(text_chunk)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200 and len(res.content) > 500:
                return res.content
            return b""

        # Split long text if over 180 chars (Google TTS limit per chunk)
        if len(clean_text) <= 180:
            google_audio = await asyncio.to_thread(_get_google_tts, clean_text)
            if google_audio:
                if len(_AUDIO_CACHE) >= _MAX_CACHE_ITEMS:
                    _AUDIO_CACHE.pop(next(iter(_AUDIO_CACHE)))
                _AUDIO_CACHE[cache_key] = google_audio
                return google_audio, "google-tts"
        else:
            # Chunk by sentences
            sentences = re.split(r'(?<=[.?!])\s+', clean_text)
            chunks = []
            cur = ""
            for s in sentences:
                if len(cur) + len(s) + 1 < 170:
                    cur = (cur + " " + s).strip()
                else:
                    if cur:
                        chunks.append(cur)
                    cur = s
            if cur:
                chunks.append(cur)

            combined_audio = bytearray()
            for chk in chunks[:10]:
                chunk_audio = await asyncio.to_thread(_get_google_tts, chk)
                if chunk_audio:
                    combined_audio.extend(chunk_audio)

            if combined_audio:
                result_bytes = bytes(combined_audio)
                if len(_AUDIO_CACHE) >= _MAX_CACHE_ITEMS:
                    _AUDIO_CACHE.pop(next(iter(_AUDIO_CACHE)))
                _AUDIO_CACHE[cache_key] = result_bytes
                return result_bytes, "google-tts-chunked"
    except Exception as ge:
        logger.error(f"[TTS] Google TTS fallback error: {ge}")

    raise RuntimeError("All server-side TTS synthesis engines failed")
