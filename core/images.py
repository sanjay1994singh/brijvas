from pathlib import Path

from PIL import Image, ImageOps


def optimize_uploaded_image(
        image_field,
        max_size=(1600, 1200),
        quality=82,
        min_quality=72,
        target_kb=450
):
    if not image_field:
        return

    image_path = getattr(image_field, "path", None)
    if not image_path:
        return

    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return

    suffix = path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        return

    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

            save_kwargs = {
                "optimize": True,
            }

            if suffix in {".jpg", ".jpeg"}:
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                save_kwargs.update(
                    format="JPEG",
                    quality=quality,
                    progressive=True,
                )
            elif suffix == ".webp":
                save_kwargs.update(
                    format="WEBP",
                    quality=quality,
                    method=6,
                )
            else:
                save_kwargs.update(
                    format="PNG",
                    compress_level=9,
                )

            image.save(path, **save_kwargs)

            if suffix == ".png":
                return

            current_quality = quality
            target_bytes = target_kb * 1024
            while path.stat().st_size > target_bytes and current_quality > min_quality:
                current_quality -= 5
                save_kwargs["quality"] = max(current_quality, min_quality)
                image.save(path, **save_kwargs)
    except OSError:
        return
