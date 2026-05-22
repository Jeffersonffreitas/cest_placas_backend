import re
from dataclasses import dataclass

from app.core.exceptions import AppException


_BR_PLATE_PATTERN = re.compile(r"[A-Z]{3}[0-9][A-Z0-9][0-9]{2}")
_PLATE_CLEANER = re.compile(r"[^A-Za-z0-9]")
_LETTER_CORRECTIONS = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "4": "A",
    "5": "S",
    "6": "G",
    "8": "B",
}
_DIGIT_CORRECTIONS = {
    "B": "8",
    "D": "0",
    "G": "6",
    "I": "1",
    "L": "1",
    "O": "0",
    "Q": "0",
    "S": "5",
    "T": "1",
    "Z": "2",
}


@dataclass(frozen=True)
class OCRPlateResult:
    plate_text: str
    confidence: float | None
    raw_text: str


def _normalize_ocr_text(text: str) -> str:
    return _PLATE_CLEANER.sub("", text).upper()


def _correct_plate_candidate_with_score(candidate: str) -> tuple[str, int] | None:
    normalized = _normalize_ocr_text(candidate)
    if len(normalized) != 7:
        return None

    chars = list(normalized)
    changes = 0
    for index in (0, 1, 2):
        corrected_char = _LETTER_CORRECTIONS.get(chars[index], chars[index])
        if corrected_char != chars[index]:
            changes += 1
        chars[index] = corrected_char
    for index in (3, 5, 6):
        corrected_char = _DIGIT_CORRECTIONS.get(chars[index], chars[index])
        if corrected_char != chars[index]:
            changes += 1
        chars[index] = corrected_char

    corrected = "".join(chars)
    if _BR_PLATE_PATTERN.fullmatch(corrected):
        return corrected, changes
    return None


def _correct_plate_candidate(candidate: str) -> str | None:
    corrected = _correct_plate_candidate_with_score(candidate)
    if corrected is None:
        return None
    return corrected[0]


def extract_plate_candidate(texts: list[str]) -> str | None:
    normalized_text = _normalize_ocr_text("".join(texts))
    direct_match = _BR_PLATE_PATTERN.search(normalized_text)
    if direct_match is not None:
        return direct_match.group(0)

    corrected_candidates: list[tuple[int, int, str]] = []
    for index in range(max(len(normalized_text) - 6, 0)):
        candidate = _correct_plate_candidate_with_score(normalized_text[index : index + 7])
        if candidate is not None:
            plate, changes = candidate
            corrected_candidates.append((changes, index, plate))

    if corrected_candidates:
        corrected_candidates.sort()
        return corrected_candidates[0][2]

    return None


def _parse_confidence(value: object) -> float | None:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence < 0:
        return None
    return confidence


def _average_confidence(confidences: list[float | None]) -> float | None:
    valid_confidences = [confidence for confidence in confidences if confidence is not None]
    if not valid_confidences:
        return None
    return round(sum(valid_confidences) / len(valid_confidences), 2)


def _preprocess_image(image: object) -> object:
    from PIL import ImageFilter, ImageOps

    grayscale_image = ImageOps.grayscale(image)
    contrasted_image = ImageOps.autocontrast(grayscale_image)
    width, height = contrasted_image.size
    if width < 1200:
        scale = 1200 / width
        contrasted_image = contrasted_image.resize((1200, int(height * scale)))
    return contrasted_image.filter(ImageFilter.SHARPEN)


def extract_plate_from_image(image_path: str) -> OCRPlateResult:
    try:
        from PIL import Image
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise AppException(
            "OCR dependencies are not installed.",
            status_code=503,
            code="ocr_unavailable",
        ) from exc

    try:
        with Image.open(image_path) as image:
            processed_image = _preprocess_image(image)
            data = pytesseract.image_to_data(
                processed_image,
                config=(
                    "--oem 3 --psm 6 "
                    "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                ),
                output_type=Output.DICT,
            )
    except pytesseract.TesseractNotFoundError as exc:
        raise AppException(
            "Tesseract OCR executable was not found.",
            status_code=503,
            code="ocr_unavailable",
        ) from exc
    except Exception as exc:
        raise AppException(
            "Could not process image for OCR.",
            status_code=400,
            code="invalid_image",
        ) from exc

    raw_texts = [str(text) for text in data.get("text", []) if str(text).strip()]
    confidences = [_parse_confidence(confidence) for confidence in data.get("conf", [])]
    plate_text = extract_plate_candidate(raw_texts)
    if plate_text is None:
        raise AppException(
            "Could not identify a Brazilian plate in the image.",
            status_code=422,
            code="plate_not_recognized",
        )

    return OCRPlateResult(
        plate_text=plate_text,
        confidence=_average_confidence(confidences),
        raw_text=" ".join(raw_texts),
    )
