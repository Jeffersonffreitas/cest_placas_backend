import re
from dataclasses import dataclass

from app.core.exceptions import AppException


_BR_PLATE_PATTERN = re.compile(r"(?:[A-Z]{3}[0-9][A-Z][0-9]{2}|[A-Z]{3}[0-9]{4})")
_PLATE_CLEANER = re.compile(r"[^A-Za-z0-9]")
_OCR_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")
_MAX_CANDIDATE_CORRECTIONS = 1
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
_OCR_CONFIGS = (
    "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "--oem 3 --psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
)


@dataclass(frozen=True)
class OCRPlateResult:
    plate_text: str
    confidence: float | None
    raw_text: str


@dataclass(frozen=True)
class _OCRAttempt:
    plate_text: str
    confidence: float | None
    raw_text: str


def _normalize_ocr_text(text: str) -> str:
    return _PLATE_CLEANER.sub("", text).upper()


def _unique_options(options: list[tuple[str, int]]) -> list[tuple[str, int]]:
    best_by_char: dict[str, int] = {}
    for char, changes in options:
        current_changes = best_by_char.get(char)
        if current_changes is None or changes < current_changes:
            best_by_char[char] = changes
    return sorted(best_by_char.items(), key=lambda option: option[1])


def _letter_options(char: str) -> list[tuple[str, int]]:
    options: list[tuple[str, int]] = []
    if char.isalpha():
        options.append((char, 0))
    corrected_char = _LETTER_CORRECTIONS.get(char)
    if corrected_char is not None:
        options.append((corrected_char, 1))
    return _unique_options(options)


def _digit_options(char: str) -> list[tuple[str, int]]:
    options: list[tuple[str, int]] = []
    if char.isdigit():
        options.append((char, 0))
    corrected_char = _DIGIT_CORRECTIONS.get(char)
    if corrected_char is not None:
        options.append((corrected_char, 1))
    return _unique_options(options)


def _flex_options(char: str) -> list[tuple[str, int]]:
    options: list[tuple[str, int]] = [(char, 0)]
    options.extend(_letter_options(char))
    options.extend(_digit_options(char))
    return _unique_options(options)


def _correct_plate_candidate_with_score(candidate: str) -> tuple[str, int] | None:
    normalized = _normalize_ocr_text(candidate)
    if len(normalized) != 7:
        return None

    options_by_position = [
        _letter_options(normalized[0]),
        _letter_options(normalized[1]),
        _letter_options(normalized[2]),
        _digit_options(normalized[3]),
        _flex_options(normalized[4]),
        _digit_options(normalized[5]),
        _digit_options(normalized[6]),
    ]
    if any(not options for options in options_by_position):
        return None

    corrected_candidates: list[tuple[int, str]] = [(0, "")]
    for position_options in options_by_position:
        next_candidates: list[tuple[int, str]] = []
        for current_changes, current_text in corrected_candidates:
            for char, char_changes in position_options:
                next_candidates.append((current_changes + char_changes, current_text + char))
        corrected_candidates = next_candidates

    valid_candidates = [
        (changes, corrected)
        for changes, corrected in corrected_candidates
        if changes <= _MAX_CANDIDATE_CORRECTIONS and _BR_PLATE_PATTERN.fullmatch(corrected)
    ]
    if not valid_candidates:
        return None

    changes, corrected = sorted(valid_candidates)[0]
    return corrected, changes


def _correct_plate_candidate(candidate: str) -> str | None:
    corrected = _correct_plate_candidate_with_score(candidate)
    if corrected is None:
        return None
    return corrected[0]


def _normalized_tokens(texts: list[str]) -> list[str]:
    tokens: list[str] = []
    for text in texts:
        for token in _OCR_TOKEN_PATTERN.findall(text):
            normalized_token = _normalize_ocr_text(token)
            if normalized_token:
                tokens.append(normalized_token)
    return tokens


def _find_direct_plate(text: str) -> str | None:
    direct_match = _BR_PLATE_PATTERN.search(text)
    if direct_match is None:
        return None
    return direct_match.group(0)


def _find_alphanumeric_plate_token(tokens: list[str]) -> str | None:
    for token in tokens:
        if len(token) == 7 and token.isalnum():
            return token
    return None


def _find_corrected_plate(texts: list[str]) -> str | None:
    corrected_candidates: list[tuple[int, int, int, int, str]] = []
    for text_index, text in enumerate(texts):
        for index in range(max(len(text) - 6, 0)):
            raw_candidate = text[index : index + 7]
            candidate = _correct_plate_candidate_with_score(raw_candidate)
            if candidate is not None:
                plate, changes = candidate
                extra_chars = abs(len(text) - 7)
                corrected_candidates.append((changes, extra_chars, text_index, -index, plate))

    if not corrected_candidates:
        return None

    corrected_candidates.sort()
    return corrected_candidates[0][4]


def extract_plate_candidate(texts: list[str]) -> str | None:
    tokens = _normalized_tokens(texts)

    for token in tokens:
        direct_plate = _find_direct_plate(token)
        if direct_plate is not None:
            return direct_plate

    corrected_plate = _find_corrected_plate(tokens)
    if corrected_plate is not None:
        return corrected_plate

    raw_plate = _find_alphanumeric_plate_token(tokens)
    if raw_plate is not None:
        return raw_plate

    normalized_text = _normalize_ocr_text("".join(tokens))
    direct_plate = _find_direct_plate(normalized_text)
    if direct_plate is not None:
        return direct_plate

    corrected_plate = _find_corrected_plate([normalized_text])
    if corrected_plate is not None:
        return corrected_plate

    if len(normalized_text) == 7 and normalized_text.isalnum():
        return normalized_text

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


def _resize_for_ocr(image: object) -> object:
    width, height = image.size
    target_width = width
    if width < 1400:
        target_width = 1400
    elif width > 2400:
        target_width = 2400

    if target_width == width:
        return image

    scale = target_width / width
    return image.resize((target_width, int(height * scale)))


def _threshold_image(image: object, threshold: int) -> object:
    return image.point(lambda pixel: 255 if pixel > threshold else 0)


def _preprocess_images(image: object) -> list[object]:
    from PIL import ImageEnhance, ImageFilter, ImageOps

    grayscale_image = ImageOps.grayscale(image)
    contrasted_image = ImageOps.autocontrast(grayscale_image)
    resized_image = _resize_for_ocr(contrasted_image)
    enhanced_image = ImageEnhance.Contrast(resized_image).enhance(1.8)
    sharpened_image = enhanced_image.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=3))
    denoised_image = sharpened_image.filter(ImageFilter.MedianFilter(size=3))
    threshold_image = _threshold_image(denoised_image, 150)
    high_threshold_image = _threshold_image(denoised_image, 185)
    inverted_threshold_image = ImageOps.invert(threshold_image)
    return [
        sharpened_image,
        denoised_image,
        threshold_image,
        high_threshold_image,
        inverted_threshold_image,
    ]


def _preprocess_image(image: object) -> object:
    return _preprocess_images(image)[0]


def _extract_texts_and_confidences(data: dict[str, object]) -> tuple[list[str], list[float | None]]:
    raw_texts: list[str] = []
    confidences: list[float | None] = []
    texts = data.get("text", [])
    raw_confidences = data.get("conf", [])
    if not isinstance(texts, list):
        return raw_texts, confidences
    if not isinstance(raw_confidences, list):
        raw_confidences = []

    for index, text in enumerate(texts):
        raw_text = str(text).strip()
        if not raw_text:
            continue
        raw_texts.append(raw_text)
        confidence = raw_confidences[index] if index < len(raw_confidences) else None
        confidences.append(_parse_confidence(confidence))
    return raw_texts, confidences


def _select_best_attempt(attempts: list[_OCRAttempt]) -> _OCRAttempt | None:
    if not attempts:
        return None
    return sorted(
        attempts,
        key=lambda attempt: (
            attempt.confidence is not None,
            attempt.confidence if attempt.confidence is not None else -1,
            len(attempt.raw_text),
        ),
        reverse=True,
    )[0]


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
            attempts: list[_OCRAttempt] = []
            all_raw_texts: list[str] = []
            for processed_image in _preprocess_images(image):
                for config in _OCR_CONFIGS:
                    data = pytesseract.image_to_data(
                        processed_image,
                        config=config,
                        output_type=Output.DICT,
                    )
                    raw_texts, confidences = _extract_texts_and_confidences(data)
                    all_raw_texts.extend(raw_texts)
                    plate_text = extract_plate_candidate(raw_texts)
                    if plate_text is not None:
                        attempts.append(
                            _OCRAttempt(
                                plate_text=plate_text,
                                confidence=_average_confidence(confidences),
                                raw_text=" ".join(raw_texts),
                            ),
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

    best_attempt = _select_best_attempt(attempts)
    if best_attempt is None:
        raise AppException(
            "Could not identify a Brazilian plate in the image.",
            status_code=422,
            code="plate_not_recognized",
        )

    return OCRPlateResult(
        plate_text=best_attempt.plate_text,
        confidence=best_attempt.confidence,
        raw_text=best_attempt.raw_text or " ".join(all_raw_texts),
    )
