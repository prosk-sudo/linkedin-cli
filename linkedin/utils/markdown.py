import re


def _to_unicode(text, style):
    """Convert ASCII letters and digits to Unicode styled characters."""
    result = []
    for ch in text:
        if 'A' <= ch <= 'Z':
            offset = ord(ch) - ord('A')
            result.append(chr(style['upper'] + offset))
        elif 'a' <= ch <= 'z':
            offset = ord(ch) - ord('a')
            result.append(chr(style['lower'] + offset))
        elif '0' <= ch <= '9' and 'digit' in style:
            offset = ord(ch) - ord('0')
            result.append(chr(style['digit'] + offset))
        else:
            result.append(ch)
    return ''.join(result)


# Unicode Mathematical Sans-Serif ranges
BOLD = {'upper': 0x1D5D4, 'lower': 0x1D5EE, 'digit': 0x1D7EC}
ITALIC = {'upper': 0x1D608, 'lower': 0x1D622}
BOLD_ITALIC = {'upper': 0x1D63C, 'lower': 0x1D656}
MONOSPACE = {'upper': 0x1D670, 'lower': 0x1D68A, 'digit': 0x1D7F6}


def _to_bold(match):
    return _to_unicode(match.group(1), BOLD)


def _to_italic(match):
    return _to_unicode(match.group(1), ITALIC)


def _to_bold_italic(match):
    return _to_unicode(match.group(1), BOLD_ITALIC)


def _to_monospace(match):
    return _to_unicode(match.group(1), MONOSPACE)


def _to_strikethrough(match):
    return ''.join(ch + '\u0336' for ch in match.group(1))


def markdown_to_linkedin(text):
    """Convert Markdown text to LinkedIn-friendly Unicode text."""
    lines = text.split('\n')
    result = []

    in_code_block = False

    for line in lines:
        # Toggle fenced code blocks (``` or ~~~)
        if re.match(r'^(`{3,}|~{3,})', line):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            result.append(line)
            continue

        # Remove images ![alt](url)
        line = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', line)

        # Convert links [text](url) → text (url)
        line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', line)

        # Headers: strip # markers, make text bold
        header_match = re.match(r'^#{1,6}\s+(.*)', line)
        if header_match:
            line = _to_unicode(header_match.group(1), BOLD)

        # Horizontal rules
        if re.match(r'^(\s*[-*_]\s*){3,}$', line):
            continue

        # Blockquotes: strip > markers
        line = re.sub(r'^(\s*>\s*)+', '', line)

        # Bold + italic ***text*** or ___text___
        line = re.sub(r'\*{3}(.+?)\*{3}', _to_bold_italic, line)
        line = re.sub(r'_{3}(.+?)_{3}', _to_bold_italic, line)

        # Bold **text** or __text__
        line = re.sub(r'\*{2}(.+?)\*{2}', _to_bold, line)
        line = re.sub(r'_{2}(.+?)_{2}', _to_bold, line)

        # Italic *text* or _text_
        line = re.sub(r'\*(.+?)\*', _to_italic, line)
        line = re.sub(r'(?<!\w)_(.+?)_(?!\w)', _to_italic, line)

        # Strikethrough ~~text~~ → combining strikethrough
        line = re.sub(r'~~(.+?)~~', _to_strikethrough, line)

        # Inline code `text` → monospace
        line = re.sub(r'`(.+?)`', _to_monospace, line)

        result.append(line)

    return '\n'.join(result).strip()
