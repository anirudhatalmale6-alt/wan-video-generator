"""Smart Dialogue Parser — extracts character dialogue from prompts
and auto-assigns voices based on character names.

Supported prompt formats:
    [Girl]: I love you my dear husband.
    [Husband]: I love you my dear wife.
    They embrace warmly under the sunset.

Also supports:
    Girl says: I love you.
    Husband says: I love you too.
    Girl: Hello there!
    Man: How are you?
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DialogueSegment:
    """A single segment of dialogue or narration."""
    character: Optional[str]  # None = narration/scene description (not spoken)
    text: str
    voice_id: str
    is_dialogue: bool  # True = spoken dialogue, False = scene description


# Character name → gender mapping for auto voice assignment
FEMALE_KEYWORDS = {
    "girl", "woman", "wife", "mother", "mom", "daughter", "sister",
    "lady", "queen", "princess", "aunt", "grandmother", "grandma",
    "she", "her", "female", "bride", "girlfriend", "miss", "mrs",
    "maid", "nurse", "actress",
}

MALE_KEYWORDS = {
    "boy", "man", "husband", "father", "dad", "son", "brother",
    "king", "prince", "uncle", "grandfather", "grandpa",
    "he", "him", "male", "groom", "boyfriend", "mr", "sir",
    "soldier", "actor",
}

# Default voice assignments
FEMALE_VOICE = "en_US-amy-medium"
FEMALE_VOICE_ALT = "en_US-lessac-high"
MALE_VOICE = "en_US-joe-medium"
MALE_VOICE_ALT = "en_US-ryan-high"
NARRATOR_VOICE = "en_US-amy-medium"


def detect_gender(character_name: str) -> str:
    """Detect gender from character name/label.

    Returns: "female", "male", or "unknown"
    """
    name_lower = character_name.lower().strip()
    words = set(re.split(r'\W+', name_lower))

    # Check direct keyword match
    if words & FEMALE_KEYWORDS:
        return "female"
    if words & MALE_KEYWORDS:
        return "male"

    # Check if any keyword is a substring
    for kw in FEMALE_KEYWORDS:
        if kw in name_lower:
            return "female"
    for kw in MALE_KEYWORDS:
        if kw in name_lower:
            return "male"

    return "unknown"


def assign_voice(character_name: str, used_voices: dict) -> str:
    """Assign a voice to a character based on their name/gender.

    Tracks used voices to avoid giving the same voice to different characters.
    Returns a voice_id string.
    """
    # If character already has a voice assigned, return it
    char_key = character_name.lower().strip()
    if char_key in used_voices:
        return used_voices[char_key]

    gender = detect_gender(character_name)

    if gender == "female":
        # Try primary female voice, then alternate
        if FEMALE_VOICE not in used_voices.values():
            voice = FEMALE_VOICE
        else:
            voice = FEMALE_VOICE_ALT
    elif gender == "male":
        if MALE_VOICE not in used_voices.values():
            voice = MALE_VOICE
        else:
            voice = MALE_VOICE_ALT
    else:
        # Unknown gender — assign based on what's available
        all_voices = [FEMALE_VOICE, MALE_VOICE, FEMALE_VOICE_ALT, MALE_VOICE_ALT]
        used = set(used_voices.values())
        voice = next((v for v in all_voices if v not in used), FEMALE_VOICE)

    used_voices[char_key] = voice
    logger.info(f"Voice assigned: '{character_name}' ({gender}) → {voice}")
    return voice


def parse_dialogue(prompt: str) -> List[DialogueSegment]:
    """Parse a prompt into dialogue segments with auto-assigned voices.

    Detects patterns like:
        [Character]: dialogue text
        Character says: dialogue text
        Character: dialogue text

    Non-dialogue text is returned as narration segments (not spoken).
    """
    used_voices = {}
    segments = []

    # Pattern 1: [Character]: text
    # Pattern 2: Character says: text
    # Pattern 3: Character: text (at start of line or after period)
    dialogue_pattern = re.compile(
        r'(?:'
        r'\[([^\]]+)\]\s*:\s*'           # [Character]: text
        r'|'
        r'(\b\w[\w\s]{0,20}?)\s+says?\s*:\s*'  # Character says: text
        r'|'
        r'(?:^|\.\s+)(\b[A-Z][\w\s]{0,15}?)\s*:\s*'  # Character: text (capitalized)
        r')'
        r'([^[\]]*?)(?=\[|\b\w[\w\s]{0,20}?\s+says?\s*:|(?:^|\.\s+)[A-Z][\w\s]{0,15}?\s*:|$)',
        re.MULTILINE
    )

    # Try to find dialogue patterns
    matches = list(dialogue_pattern.finditer(prompt))

    if not matches:
        # No dialogue detected — treat entire prompt as single narration
        # that will be read as voice
        return [DialogueSegment(
            character=None,
            text=prompt.strip(),
            voice_id=NARRATOR_VOICE,
            is_dialogue=False,
        )]

    last_end = 0

    for match in matches:
        # Get any text before this dialogue (scene description)
        pre_text = prompt[last_end:match.start()].strip()
        if pre_text:
            # Remove trailing punctuation artifacts
            pre_text = pre_text.strip(". \n\t")
            if pre_text:
                segments.append(DialogueSegment(
                    character=None,
                    text=pre_text,
                    voice_id=NARRATOR_VOICE,
                    is_dialogue=False,
                ))

        # Get character name from whichever group matched
        character = match.group(1) or match.group(2) or match.group(3)
        dialogue_text = match.group(4).strip().rstrip(".")

        if character and dialogue_text:
            character = character.strip()
            voice = assign_voice(character, used_voices)
            segments.append(DialogueSegment(
                character=character,
                text=dialogue_text,
                voice_id=voice,
                is_dialogue=True,
            ))

        last_end = match.end()

    # Any remaining text after last dialogue
    remaining = prompt[last_end:].strip()
    if remaining:
        remaining = remaining.strip(". \n\t")
        if remaining:
            segments.append(DialogueSegment(
                character=None,
                text=remaining,
                voice_id=NARRATOR_VOICE,
                is_dialogue=False,
            ))

    # If no dialogue was actually found in the matches, return as single segment
    if not any(s.is_dialogue for s in segments):
        return [DialogueSegment(
            character=None,
            text=prompt.strip(),
            voice_id=NARRATOR_VOICE,
            is_dialogue=False,
        )]

    return segments


def get_voice_summary(segments: List[DialogueSegment]) -> str:
    """Get a human-readable summary of voice assignments."""
    characters = {}
    for seg in segments:
        if seg.is_dialogue and seg.character:
            if seg.character not in characters:
                characters[seg.character] = seg.voice_id

    if not characters:
        return "Single narrator voice"

    lines = []
    for char, voice in characters.items():
        gender = detect_gender(char)
        lines.append(f"  {char} ({gender}) → {voice}")

    return "Voice assignments:\n" + "\n".join(lines)
