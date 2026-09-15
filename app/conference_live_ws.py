import asyncio
import json
import logging
import os
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

logger = logging.getLogger("uvicorn.error")

VALID_VOICES = {
    "puck": "Puck",       # Friendly, energetic male
    "charon": "Charon",   # Deep, calm male
    "fenrir": "Fenrir",   # Authoritative male
    "kore": "Kore",       # Natural, relaxed female
    "aoede": "Aoede",     # Warm, expressive female
}
DEFAULT_VOICE = "Puck"


async def handle_conference_live_websocket(
    websocket: WebSocket,
    role: str = "Senior Software Engineer",
    company: str = "Global Employer",
    voice: str = "Puck",
    user_name: Optional[str] = None
):
    """
    Manages low-latency bidirectional voice-to-voice communication between candidate browser
    and Google Gemini Live Multimodal API (gemini-2.5-flash-native-audio-latest).
    
    Streams raw 24kHz PCM audio chunks directly to browser with sub-800ms latency.
    """
    await websocket.accept()
    api_key = os.getenv("GEMINI_API_KEY")
    logger.info(f"[Gemini Live WS] Client connected for role: '{role}' at '{company}'")
    if not api_key:
        await websocket.send_json({
            "type": "error",
            "message": "Gemini API key is not configured on server."
        })
        await websocket.close()
        return

    # Normalize voice
    normalized_voice = voice.strip().lower() if voice else "puck"
    selected_voice = VALID_VOICES.get(normalized_voice, DEFAULT_VOICE)

    system_prompt = f"""You are Alex, a senior technical interviewer and hiring manager conducting a live technical video interview with {user_name or 'the candidate'} for the role of {role} at {company or 'our engineering team'}.

CRITICAL CONVERSATIONAL RULES FOR LIVE ORAL INTERVIEWS:
1. Speak in a natural, engaging, professional speaking tone.
2. Keep your spoken responses concise and brief: exactly 1 to 2 short sentences per turn (maximum 20-35 words per turn). This is essential so the interview feels like an authentic real-time human conversation, not a lecture.
3. Ask only ONE question at a time.
4. Listen carefully to the candidate. When they answer, briefly acknowledge what they said with 4-7 words, and immediately ask the next relevant question or scenario.
5. If the candidate makes a clear technical mistake or misunderstands a core concept, gently point it out or ask a guiding follow-up question so they can correct themselves.
6. When starting the call, warmly greet {user_name or 'the candidate'} in one sentence and ask your opening question."""

    try:
        client = genai.Client(api_key=api_key)
        live_config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=selected_voice)
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=system_prompt)]
            )
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[Gemini Live WS] Failed to configure Gemini Live client: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to initialize Gemini Live config: {str(e)}"
        })
        await websocket.close()
        return

    try:
        async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-latest", config=live_config) as session:
            # Notify client that Gemini Live is connected and ready
            await websocket.send_json({
                "type": "ready",
                "voice": selected_voice,
                "role": role,
                "sample_rate": 24000
            })
            logger.info(f"[Gemini Live WS] Connected to Gemini Live session with voice {selected_voice}")

            async def client_to_gemini():
                """Forward client text turns or binary audio to Gemini Live."""
                try:
                    while True:
                        msg = await websocket.receive()
                        if "text" in msg and msg["text"]:
                            data = json.loads(msg["text"])
                            msg_type = data.get("type")

                            if msg_type == "start":
                                # Trigger opening greeting
                                prompt = f"The candidate ({user_name or 'the applicant'}) has entered the room. Greet them and ask your first interview question."
                                await session.send_client_content(
                                    turns=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                                    turn_complete=True
                                )

                            elif msg_type == "candidate_turn":
                                candidate_text = data.get("text", "").strip()
                                if candidate_text:
                                    await session.send_client_content(
                                        turns=[types.Content(role="user", parts=[types.Part.from_text(text=candidate_text)])],
                                        turn_complete=True
                                    )

                            elif msg_type == "ping":
                                await websocket.send_json({"type": "pong"})

                        elif "bytes" in msg and msg["bytes"]:
                            # Stream candidate microphone raw audio (PCM 16kHz) directly to Gemini
                            pcm_data = msg["bytes"]
                            await session.send_realtime_input(
                                audio=types.Blob(data=pcm_data, mime_type="audio/pcm;rate=16000")
                            )

                except WebSocketDisconnect:
                    logger.info("[Gemini Live WS] Client disconnected cleanly")
                except asyncio.CancelledError:
                    pass
                except Exception as ex:
                    logger.warning(f"[Gemini Live WS] Exception in client_to_gemini: {ex}")

            async def gemini_to_client():
                """Stream Gemini Live audio chunks and transcription back to client continuously across all conversation turns."""
                try:
                    while True:
                        try:
                            response = await session._receive()
                            if not response:
                                continue
                            sc = response.server_content
                            if sc and sc.model_turn:
                                for part in sc.model_turn.parts:
                                    # Stream raw 24kHz PCM audio chunk directly as binary frame
                                    if part.inline_data and part.inline_data.data:
                                        await websocket.send_bytes(part.inline_data.data)

                                    # If model returns thought or text, send as subtitle frame
                                    if part.text:
                                        clean_sub = part.text.strip()
                                        if clean_sub and not clean_sub.startswith("**"):
                                            await websocket.send_json({
                                                "type": "subtitle",
                                                "text": clean_sub
                                            })

                            if sc and sc.turn_complete:
                                await websocket.send_json({"type": "turn_complete"})
                        except (asyncio.CancelledError, WebSocketDisconnect):
                            break
                        except Exception as loop_ex:
                            err_str = str(loop_ex).lower()
                            if "closed" in err_str or "1000" in err_str or "1001" in err_str:
                                break
                            logger.warning(f"[Gemini Live WS] Turn receive loop warning: {loop_ex}")
                            await asyncio.sleep(0.05)

                except WebSocketDisconnect:
                    logger.info("[Gemini Live WS] Client disconnected during receive")
                except asyncio.CancelledError:
                    pass
                except Exception as ex:
                    logger.warning(f"[Gemini Live WS] Exception in gemini_to_client: {ex}")

            # Run both bidirectional loops concurrently
            producer = asyncio.create_task(client_to_gemini())
            consumer = asyncio.create_task(gemini_to_client())

            done, pending = await asyncio.wait(
                [producer, consumer],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

    except WebSocketDisconnect:
        logger.info("[Gemini Live WS] Session ended: WebSocket disconnected")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[Gemini Live WS] Live session error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Gemini Live session error: {str(e)}"
            })
        except Exception:
            pass
