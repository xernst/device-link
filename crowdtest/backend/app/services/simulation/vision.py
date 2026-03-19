"""Vision engine: multimodal image analysis for social posts.

Uses Claude's vision capabilities to analyze images in marketing materials
so simulation agents can react to what they SEE, not just what they read.

Pipeline:
1. Image uploaded → stored locally or S3
2. Vision analysis → structured description of the image
3. Description injected into agent prompts alongside text content
4. Agents react to the full social post (text + visual)
"""

import base64
import hashlib
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.core.config import settings


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO_THUMBNAIL = "video_thumbnail"  # we analyze the thumbnail, not the video
    CAROUSEL = "carousel"  # multiple images
    GIF = "gif"


SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB (Claude vision limit)

# Local storage path (S3 in production)
UPLOAD_DIR = Path(os.getenv("CROWDTEST_UPLOAD_DIR", "/tmp/crowdtest-uploads"))


@dataclass
class VisualAnalysis:
    """Structured output from vision analysis of a social post image."""
    # Core description
    description: str  # what the image shows (1-2 sentences)
    visual_elements: list[str]  # key visual components (e.g., "product photo", "bold text overlay")

    # Social post specifics
    text_in_image: str | None  # any text visible in the image (OCR-like)
    brand_elements: list[str]  # logos, brand colors, watermarks
    people: list[dict]  # [{"count": 2, "description": "young professionals smiling"}]
    products: list[str]  # products/items visible

    # Tone & style
    visual_tone: str  # professional, casual, edgy, luxurious, minimalist, etc.
    color_palette: list[str]  # dominant colors
    style_tags: list[str]  # flat-lay, lifestyle, UGC, studio, meme, infographic, etc.

    # Platform fit
    platform_fit: dict  # {"twitter": 0.8, "instagram": 0.9, "linkedin": 0.6, "reddit": 0.4}
    scroll_stopping_score: float  # 0-1, how likely to stop a thumb-scroll

    # Engagement predictions
    emotional_appeal: str  # aspirational, fear, humor, curiosity, outrage, etc.
    likely_reactions: list[str]  # predicted reaction types based on visual

    # Humor & tone analysis
    humor_type: str | None  # meme, satire, parody, irony, shitpost, wholesome, none
    humor_format: str | None  # recognized meme template name if applicable
    humor_execution_score: float  # 0-1, how well the humor lands (0 = cringe, 1 = perfect)
    cringe_risk: float  # 0-1, probability of being perceived as "fellow kids" cringe
    irony_detected: bool  # is the image/text using irony or sarcasm?
    reference_type: str | None  # pop culture, internet culture, niche community, none

    # Raw data
    image_hash: str  # for dedup
    dimensions: tuple[int, int] | None  # width x height
    file_size_bytes: int = 0
    media_type: MediaType = MediaType.IMAGE


# ──────────────────────────────────────────────────────────────────────
# Vision Analysis Prompts
# ──────────────────────────────────────────────────────────────────────

VISION_ANALYSIS_SYSTEM = """You are a social media visual analyst with deep fluency in internet culture, meme formats, and social media humor.

You analyze images from marketing materials and social posts to help simulate how real people would react to them in their feed.

Your analysis should capture:
1. What a person scrolling sees in 1-3 seconds
2. Deeper elements they'd notice if they stopped
3. HUMOR ANALYSIS: Is this trying to be funny? What kind of humor? Does it land? Would internet-savvy people cringe or laugh? Is it using a recognizable meme format? Is there irony or sarcasm? Could this become a meme itself (intentionally or not)?

You are an expert at detecting: meme formats (Drake, distracted boyfriend, galaxy brain, wojak, etc.), corporate cringe, intentional shitposting, irony layers, cultural references, and the difference between brands that "get it" and brands that are trying too hard.

Return structured JSON."""

VISION_ANALYSIS_USER = """Analyze this social media image/creative for a {platform} post.

Context: This image will be shown alongside this text content:
{text_content}

Industry: {industry}

Return JSON with these fields:
{{
  "description": "What the image shows (1-2 sentences, as a person would describe it)",
  "visual_elements": ["list of key visual components"],
  "text_in_image": "any text visible in the image (null if none)",
  "brand_elements": ["logos, brand colors, watermarks visible"],
  "people": [{{"count": 1, "description": "who they are and what they're doing"}}],
  "products": ["products or items visible"],
  "visual_tone": "one word: professional/casual/edgy/luxurious/minimalist/playful/corporate/authentic",
  "color_palette": ["dominant colors"],
  "style_tags": ["flat-lay", "lifestyle", "UGC", "studio", "meme", "infographic", etc.],
  "platform_fit": {{"twitter": 0.0-1.0, "reddit": 0.0-1.0, "instagram": 0.0-1.0, "linkedin": 0.0-1.0}},
  "scroll_stopping_score": 0.0-1.0,
  "emotional_appeal": "primary emotional trigger",
  "likely_reactions": ["predicted reaction types"],
  "humor_type": "meme/satire/parody/irony/shitpost/wholesome/cringe_attempt/none",
  "humor_format": "name of recognized meme template if applicable, else null",
  "humor_execution_score": 0.0-1.0 (how well the humor lands; 0=cringe 1=perfect; null if not humor),
  "cringe_risk": 0.0-1.0 (probability of being perceived as 'fellow kids' corporate cringe),
  "irony_detected": true/false (is the image/text using irony, sarcasm, or saying the opposite of what it means?),
  "reference_type": "pop_culture/internet_culture/niche_community/current_events/none"
}}"""

# Prompt for generating what agents "see" — injected into batch reaction prompts
VISUAL_CONTEXT_TEMPLATE = """## Visual Content
The post includes an image: {description}
Visual tone: {visual_tone}. Style: {style_tags}.
{text_in_image_line}
{people_line}
{products_line}
Scroll-stopping score: {scroll_stopping_score}/10 — {scroll_stopping_note}
{humor_line}"""


# ──────────────────────────────────────────────────────────────────────
# Image Storage
# ──────────────────────────────────────────────────────────────────────

def save_uploaded_image(file_bytes: bytes, content_type: str, filename: str) -> dict:
    """Save an uploaded image and return storage metadata.

    Returns: {"path": str, "hash": str, "size": int, "media_type": str}
    """
    if content_type not in SUPPORTED_IMAGE_TYPES:
        raise ValueError(f"Unsupported image type: {content_type}. Supported: {list(SUPPORTED_IMAGE_TYPES.keys())}")

    if len(file_bytes) > MAX_IMAGE_SIZE:
        raise ValueError(f"Image too large: {len(file_bytes)} bytes. Max: {MAX_IMAGE_SIZE} bytes")

    # Generate content hash for dedup
    image_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
    ext = SUPPORTED_IMAGE_TYPES[content_type]
    stored_filename = f"{image_hash}.{ext}"

    # Ensure upload dir exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filepath = UPLOAD_DIR / stored_filename

    # Skip if already stored (dedup by hash)
    if not filepath.exists():
        filepath.write_bytes(file_bytes)

    return {
        "path": str(filepath),
        "hash": image_hash,
        "size": len(file_bytes),
        "media_type": content_type,
        "filename": stored_filename,
    }


def load_image_as_base64(filepath: str) -> tuple[str, str]:
    """Load an image file and return (base64_data, media_type) for Claude vision API."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {filepath}")

    file_bytes = path.read_bytes()
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    # Determine media type from extension
    ext = path.suffix.lower().lstrip(".")
    ext_to_mime = {v: k for k, v in SUPPORTED_IMAGE_TYPES.items()}
    media_type = ext_to_mime.get(ext, "image/png")

    return b64, media_type


# ──────────────────────────────────────────────────────────────────────
# Vision Analysis (Claude multimodal)
# ──────────────────────────────────────────────────────────────────────

async def analyze_image(
    image_path: str,
    text_content: str = "",
    platform: str = "twitter",
    industry: str = "",
) -> VisualAnalysis:
    """Analyze an image using Claude's vision capabilities.

    Sends the image to Claude with the vision analysis prompt and returns
    a structured VisualAnalysis object.
    """
    import anthropic

    b64_data, media_type = load_image_as_base64(image_path)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=settings.sonnet_model,
        max_tokens=1024,
        system=VISION_ANALYSIS_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data,
                    },
                },
                {
                    "type": "text",
                    "text": VISION_ANALYSIS_USER.format(
                        platform=platform,
                        text_content=text_content or "(no text content)",
                        industry=industry or "general",
                    ),
                },
            ],
        }],
    )

    # Parse JSON response
    import json
    raw = response.content[0].text
    # Handle markdown code fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)

    image_hash = hashlib.sha256(Path(image_path).read_bytes()).hexdigest()[:16]

    return VisualAnalysis(
        description=data.get("description", ""),
        visual_elements=data.get("visual_elements", []),
        text_in_image=data.get("text_in_image"),
        brand_elements=data.get("brand_elements", []),
        people=data.get("people", []),
        products=data.get("products", []),
        visual_tone=data.get("visual_tone", ""),
        color_palette=data.get("color_palette", []),
        style_tags=data.get("style_tags", []),
        platform_fit=data.get("platform_fit", {}),
        scroll_stopping_score=data.get("scroll_stopping_score", 0.5),
        emotional_appeal=data.get("emotional_appeal", ""),
        likely_reactions=data.get("likely_reactions", []),
        humor_type=data.get("humor_type"),
        humor_format=data.get("humor_format"),
        humor_execution_score=data.get("humor_execution_score", 0.0),
        cringe_risk=data.get("cringe_risk", 0.0),
        irony_detected=data.get("irony_detected", False),
        reference_type=data.get("reference_type"),
        image_hash=image_hash,
        dimensions=None,  # TODO: extract from image metadata
        file_size_bytes=Path(image_path).stat().st_size,
    )


async def analyze_carousel(
    image_paths: list[str],
    text_content: str = "",
    platform: str = "instagram",
    industry: str = "",
) -> list[VisualAnalysis]:
    """Analyze multiple images (carousel post). Returns analysis for each slide."""
    results = []
    for i, path in enumerate(image_paths):
        analysis = await analyze_image(
            path,
            text_content=f"[Slide {i + 1}/{len(image_paths)}] {text_content}",
            platform=platform,
            industry=industry,
        )
        analysis.media_type = MediaType.CAROUSEL
        results.append(analysis)
    return results


# ──────────────────────────────────────────────────────────────────────
# Visual Context Generation (for agent prompts)
# ──────────────────────────────────────────────────────────────────────

def build_visual_context(analysis: VisualAnalysis) -> str:
    """Convert a VisualAnalysis into a text block for agent prompts.

    This is what agents "see" — a structured description of the visual content
    that gets injected into their reaction prompt alongside the text content.
    """
    text_line = ""
    if analysis.text_in_image:
        text_line = f"Text overlay in image: \"{analysis.text_in_image}\""

    people_line = ""
    if analysis.people:
        people_desc = "; ".join(
            f"{p.get('count', 1)} {p.get('description', 'person')}"
            for p in analysis.people
        )
        people_line = f"People in image: {people_desc}"

    products_line = ""
    if analysis.products:
        products_line = f"Products shown: {', '.join(analysis.products)}"

    score = analysis.scroll_stopping_score
    if score >= 0.8:
        scroll_note = "highly eye-catching, likely to stop scrolling"
    elif score >= 0.5:
        scroll_note = "moderately attention-grabbing"
    else:
        scroll_note = "easy to scroll past"

    # Build humor context line
    humor_line = ""
    if analysis.humor_type and analysis.humor_type != "none":
        humor_parts = [f"Humor detected: {analysis.humor_type}"]
        if analysis.humor_format:
            humor_parts.append(f"(uses '{analysis.humor_format}' format)")
        exec_score = analysis.humor_execution_score
        if exec_score >= 0.7:
            humor_parts.append("— well executed, likely to land")
        elif exec_score >= 0.4:
            humor_parts.append("— decent attempt, mixed reactions expected")
        else:
            humor_parts.append("— weak execution, cringe risk is high")
        if analysis.cringe_risk > 0.5:
            humor_parts.append(f"⚠️ Cringe risk: {analysis.cringe_risk:.0%} (may trigger 'fellow kids' reactions)")
        if analysis.irony_detected:
            humor_parts.append("Uses irony/sarcasm — will split audiences (some won't get it)")
        if analysis.reference_type and analysis.reference_type != "none":
            humor_parts.append(f"References: {analysis.reference_type}")
        humor_line = " ".join(humor_parts)

    return VISUAL_CONTEXT_TEMPLATE.format(
        description=analysis.description,
        visual_tone=analysis.visual_tone,
        style_tags=", ".join(analysis.style_tags) if analysis.style_tags else "standard",
        text_in_image_line=text_line,
        people_line=people_line,
        products_line=products_line,
        scroll_stopping_score=round(score * 10, 1),
        scroll_stopping_note=scroll_note,
        humor_line=humor_line,
    )


def build_carousel_context(analyses: list[VisualAnalysis]) -> str:
    """Build visual context for a carousel post (multiple images)."""
    parts = []
    for i, analysis in enumerate(analyses):
        parts.append(f"### Slide {i + 1}")
        parts.append(build_visual_context(analysis))
    return "\n\n".join(parts)
