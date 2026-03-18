"""Materials API: upload text + image content for simulation testing."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.simulation.vision import (
    SUPPORTED_IMAGE_TYPES,
    MediaType,
    analyze_carousel,
    analyze_image,
    build_carousel_context,
    build_visual_context,
    save_uploaded_image,
)

router = APIRouter()


@router.post("/")
async def create_material(
    project_id: str = Form(...),
    type: str = Form(...),  # ad_copy, landing_page, email, social_post
    content: str = Form(...),  # text content
    title: str = Form(None),
    platform: str = Form("twitter"),
    variant_label: str = Form(None),
    industry: str = Form(""),
    images: list[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload marketing material with optional image(s).

    Accepts multipart form data:
    - Text content (required)
    - One or more images (optional) — analyzed via Claude vision
    - Returns the material with visual analysis if images provided
    """
    from app.models.models import Material

    # Process images if provided
    media_type = None
    media_paths = []
    visual_analysis_data = None
    visual_context = None

    if images and images[0].filename:  # FastAPI sends empty UploadFile when no file
        # Validate and save images
        for img in images:
            if img.content_type not in SUPPORTED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image type: {img.content_type}. Supported: {list(SUPPORTED_IMAGE_TYPES.keys())}",
                )
            file_bytes = await img.read()
            storage_info = save_uploaded_image(file_bytes, img.content_type, img.filename)
            media_paths.append(storage_info["path"])

        # Determine media type
        if len(media_paths) == 1:
            media_type = MediaType.IMAGE.value
            # Analyze single image
            analysis = await analyze_image(
                media_paths[0],
                text_content=content,
                platform=platform,
                industry=industry,
            )
            visual_analysis_data = {
                "description": analysis.description,
                "visual_elements": analysis.visual_elements,
                "text_in_image": analysis.text_in_image,
                "brand_elements": analysis.brand_elements,
                "people": analysis.people,
                "products": analysis.products,
                "visual_tone": analysis.visual_tone,
                "color_palette": analysis.color_palette,
                "style_tags": analysis.style_tags,
                "platform_fit": analysis.platform_fit,
                "scroll_stopping_score": analysis.scroll_stopping_score,
                "emotional_appeal": analysis.emotional_appeal,
                "likely_reactions": analysis.likely_reactions,
                "image_hash": analysis.image_hash,
            }
            visual_context = build_visual_context(analysis)
        else:
            media_type = MediaType.CAROUSEL.value
            # Analyze carousel
            analyses = await analyze_carousel(
                media_paths,
                text_content=content,
                platform=platform,
                industry=industry,
            )
            visual_analysis_data = [
                {
                    "slide": i + 1,
                    "description": a.description,
                    "visual_elements": a.visual_elements,
                    "text_in_image": a.text_in_image,
                    "visual_tone": a.visual_tone,
                    "scroll_stopping_score": a.scroll_stopping_score,
                    "emotional_appeal": a.emotional_appeal,
                }
                for i, a in enumerate(analyses)
            ]
            visual_context = build_carousel_context(analyses)

    # Create material record
    material = Material(
        project_id=project_id,
        type=type,
        title=title,
        content=content,
        platform=platform,
        variant_label=variant_label,
        media_type=media_type,
        media_paths=media_paths if media_paths else None,
        visual_analysis=visual_analysis_data,
        visual_context=visual_context,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    return {
        "id": str(material.id),
        "type": material.type,
        "title": material.title,
        "content": material.content,
        "platform": material.platform,
        "has_visual": media_type is not None,
        "media_type": media_type,
        "image_count": len(media_paths),
        "visual_analysis": visual_analysis_data,
        "visual_context_preview": visual_context[:500] if visual_context else None,
    }


@router.get("/{material_id}")
async def get_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """Get material details including visual analysis."""
    from sqlalchemy import select
    from app.models.models import Material

    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return {
        "id": str(material.id),
        "project_id": str(material.project_id),
        "type": material.type,
        "title": material.title,
        "content": material.content,
        "platform": material.platform,
        "variant_label": material.variant_label,
        "has_visual": material.media_type is not None,
        "media_type": material.media_type,
        "media_paths": material.media_paths,
        "visual_analysis": material.visual_analysis,
        "visual_context": material.visual_context,
        "created_at": material.created_at.isoformat() if material.created_at else None,
    }
