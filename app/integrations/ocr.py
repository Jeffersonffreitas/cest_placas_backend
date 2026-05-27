import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.exceptions import AppException


_WINDOWS_TESSERACT_COMMANDS = (
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)
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
    "A": "4",
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
    "--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "--oem 3 --psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "--oem 3 --psm 13 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
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
    corrections: int
    extra_chars: int
    is_direct: bool
    is_pattern: bool


@dataclass(frozen=True)
class _OCRToken:
    text: str
    confidence: float | None
    index: int


@dataclass(frozen=True)
class _PlateCandidate:
    plate_text: str
    confidence: float | None
    corrections: int
    extra_chars: int
    token_index: int
    start_index: int
    source_text: str
    is_direct: bool
    is_pattern: bool
    is_joined: bool


def _is_existing_file(path: str) -> bool:
    try:
        return Path(path).is_file()
    except OSError:
        return False


def _resolve_tesseract_command() -> str | None:
    candidates: list[str] = []
    if sys.platform.startswith("win"):
        candidates.extend(_WINDOWS_TESSERACT_COMMANDS)

    path_command = shutil.which("tesseract")
    if path_command is not None:
        candidates.append(path_command)

    for candidate in candidates:
        if _is_existing_file(candidate):
            return candidate

    return path_command


def _configure_tesseract_executable(pytesseract_module: Any) -> None:
    command = _resolve_tesseract_command()
    if command is not None:
        pytesseract_module.pytesseract.tesseract_cmd = command


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


def _normalized_tokens_with_confidences(
    texts: list[str],
    confidences: list[float | None] | None = None,
) -> list[_OCRToken]:
    tokens: list[_OCRToken] = []
    for text_index, text in enumerate(texts):
        for token in _OCR_TOKEN_PATTERN.findall(text):
            normalized_token = _normalize_ocr_text(token)
            if normalized_token:
                confidence = (
                    confidences[text_index]
                    if confidences and text_index < len(confidences)
                    else None
                )
                tokens.append(
                    _OCRToken(text=normalized_token, confidence=confidence, index=text_index),
                )
    return tokens


def _candidate_sort_key(candidate: _PlateCandidate) -> tuple[int, int, int, int, int, int, int, float]:
    confidence = candidate.confidence if candidate.confidence is not None else -1
    return (
        0 if candidate.is_pattern else 1,
        candidate.corrections,
        0 if candidate.is_direct else 1,
        candidate.extra_chars,
        1 if candidate.is_joined else 0,
        candidate.token_index,
        candidate.start_index,
        -confidence,
    )


def _candidate_confidence(tokens: list[_OCRToken]) -> float | None:
    return _average_confidence([token.confidence for token in tokens])


def _append_candidate(
    candidates: list[_PlateCandidate],
    seen_candidates: set[tuple[str, int, int, int, bool, bool]],
    *,
    plate_text: str,
    confidence: float | None,
    corrections: int,
    extra_chars: int,
    token_index: int,
    start_index: int,
    source_text: str,
    is_direct: bool,
    is_joined: bool,
) -> None:
    is_pattern = _BR_PLATE_PATTERN.fullmatch(plate_text) is not None
    key = (plate_text, corrections, token_index, start_index, is_direct, is_joined)
    if key in seen_candidates:
        return
    seen_candidates.add(key)
    candidates.append(
        _PlateCandidate(
            plate_text=plate_text,
            confidence=confidence,
            corrections=corrections,
            extra_chars=extra_chars,
            token_index=token_index,
            start_index=start_index,
            source_text=source_text,
            is_direct=is_direct,
            is_pattern=is_pattern,
            is_joined=is_joined,
        ),
    )


def _extract_plate_candidates_from_token(
    token: _OCRToken,
    *,
    is_joined: bool,
) -> list[_PlateCandidate]:
    candidates: list[_PlateCandidate] = []
    seen_candidates: set[tuple[str, int, int, int, bool, bool]] = set()
    text = token.text

    for direct_match in _BR_PLATE_PATTERN.finditer(text):
        plate_text = direct_match.group(0)
        _append_candidate(
            candidates,
            seen_candidates,
            plate_text=plate_text,
            confidence=token.confidence,
            corrections=0,
            extra_chars=abs(len(text) - 7),
            token_index=token.index,
            start_index=direct_match.start(),
            source_text=text,
            is_direct=True,
            is_joined=is_joined,
        )

    for index in range(max(len(text) - 6, 0)):
        raw_candidate = text[index : index + 7]
        corrected_candidate = _correct_plate_candidate_with_score(raw_candidate)
        if corrected_candidate is None:
            continue
        plate_text, corrections = corrected_candidate
        _append_candidate(
            candidates,
            seen_candidates,
            plate_text=plate_text,
            confidence=token.confidence,
            corrections=corrections,
            extra_chars=abs(len(text) - 7),
            token_index=token.index,
            start_index=index,
            source_text=text,
            is_direct=corrections == 0,
            is_joined=is_joined,
        )

    if len(text) == 7 and text.isalnum() and _BR_PLATE_PATTERN.fullmatch(text) is None:
        _append_candidate(
            candidates,
            seen_candidates,
            plate_text=text,
            confidence=token.confidence,
            corrections=2,
            extra_chars=0,
            token_index=token.index,
            start_index=0,
            source_text=text,
            is_direct=False,
            is_joined=is_joined,
        )

    return sorted(candidates, key=_candidate_sort_key)


def _extract_plate_candidates(
    texts: list[str],
    confidences: list[float | None] | None = None,
) -> list[_PlateCandidate]:
    tokens = _normalized_tokens_with_confidences(texts, confidences)
    candidates: list[_PlateCandidate] = []
    seen_candidates: set[tuple[str, int, int, int, bool, bool]] = set()

    for token in tokens:
        for candidate in _extract_plate_candidates_from_token(token, is_joined=False):
            _append_candidate(
                candidates,
                seen_candidates,
                plate_text=candidate.plate_text,
                confidence=candidate.confidence,
                corrections=candidate.corrections,
                extra_chars=candidate.extra_chars,
                token_index=candidate.token_index,
                start_index=candidate.start_index,
                source_text=candidate.source_text,
                is_direct=candidate.is_direct,
                is_joined=candidate.is_joined,
            )

    if tokens:
        joined_text = "".join(token.text for token in tokens)
        joined_token = _OCRToken(
            text=joined_text,
            confidence=_candidate_confidence(tokens),
            index=len(tokens),
        )
        for candidate in _extract_plate_candidates_from_token(joined_token, is_joined=True):
            _append_candidate(
                candidates,
                seen_candidates,
                plate_text=candidate.plate_text,
                confidence=candidate.confidence,
                corrections=candidate.corrections,
                extra_chars=candidate.extra_chars,
                token_index=candidate.token_index,
                start_index=candidate.start_index,
                source_text=candidate.source_text,
                is_direct=candidate.is_direct,
                is_joined=candidate.is_joined,
            )

    return sorted(candidates, key=_candidate_sort_key)


def extract_plate_candidate(texts: list[str]) -> str | None:
    candidates = _extract_plate_candidates(texts)
    if not candidates:
        return None
    return candidates[0].plate_text


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
    normalized_image = ImageOps.autocontrast(resized_image)
    enhanced_image = ImageEnhance.Contrast(resized_image).enhance(1.8)
    high_contrast_image = ImageEnhance.Contrast(resized_image).enhance(2.4)
    sharpened_image = enhanced_image.filter(
        ImageFilter.UnsharpMask(radius=2, percent=180, threshold=3),
    )
    strong_sharpened_image = high_contrast_image.filter(
        ImageFilter.UnsharpMask(radius=1, percent=240, threshold=2),
    )
    denoised_image = sharpened_image.filter(ImageFilter.MedianFilter(size=3))
    light_threshold_image = _threshold_image(denoised_image, 120)
    threshold_image = _threshold_image(denoised_image, 150)
    high_threshold_image = _threshold_image(denoised_image, 185)
    strong_threshold_image = _threshold_image(strong_sharpened_image, 165)
    inverted_threshold_image = ImageOps.invert(threshold_image)
    inverted_high_threshold_image = ImageOps.invert(high_threshold_image)
    return [
        normalized_image,
        sharpened_image,
        strong_sharpened_image,
        denoised_image,
        light_threshold_image,
        threshold_image,
        high_threshold_image,
        strong_threshold_image,
        inverted_threshold_image,
        inverted_high_threshold_image,
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

    grouped_attempts: dict[str, list[_OCRAttempt]] = {}
    for attempt in attempts:
        grouped_attempts.setdefault(attempt.plate_text, []).append(attempt)

    def group_score(
        plate_attempts: list[_OCRAttempt],
    ) -> tuple[int, int, int, float, float, int, int, int]:
        confidences = [attempt.confidence for attempt in plate_attempts if attempt.confidence is not None]
        best_confidence = max(confidences) if confidences else -1
        average_confidence = sum(confidences) / len(confidences) if confidences else -1
        direct_count = sum(1 for attempt in plate_attempts if attempt.is_direct)
        return (
            1 if any(attempt.is_pattern for attempt in plate_attempts) else 0,
            len(plate_attempts),
            1 if confidences else 0,
            best_confidence,
            average_confidence,
            direct_count,
            -min(attempt.corrections for attempt in plate_attempts),
            -min(attempt.extra_chars for attempt in plate_attempts),
        )

    best_plate_attempts = sorted(grouped_attempts.values(), key=group_score, reverse=True)[0]
    return sorted(
        best_plate_attempts,
        key=lambda attempt: (
            attempt.confidence is not None,
            attempt.confidence if attempt.confidence is not None else -1,
            attempt.is_direct,
            -attempt.corrections,
            -attempt.extra_chars,
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

    _configure_tesseract_executable(pytesseract)

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
                    candidates = _extract_plate_candidates(raw_texts, confidences)
                    for candidate in candidates:
                        attempts.append(
                            _OCRAttempt(
                                plate_text=candidate.plate_text,
                                confidence=candidate.confidence,
                                raw_text=" ".join(raw_texts),
                                corrections=candidate.corrections,
                                extra_chars=candidate.extra_chars,
                                is_direct=candidate.is_direct,
                                is_pattern=candidate.is_pattern,
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
