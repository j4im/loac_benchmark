"""PDF parsing and rule extraction for LOAC manual."""

import re
import json
from typing import Dict, List, Optional
import pdfplumber


def parse_document(pdf_path: str, section_prefix: Optional[str] = None) -> Dict:
    """
    Parse PDF and extract hierarchical section structure.

    Args:
        pdf_path: Path to PDF file
        section_prefix: Optional section prefix to filter (e.g., "5.5" includes 5.5, 5.5.1, 5.5.2, etc.)

    Returns nested dictionary with sections, preserving:
    - Section numbers and titles (e.g., "5.5 DISCRIMINATION IN CONDUCTING ATTACKS")
    - Parent-child relationships
    - Full text content (excluding footnotes at bottom of pages)
    - Footnote references and content
    - Page numbers
    """
    sections = {}
    current_section_id = None
    current_section_text = []
    current_section_title = None
    current_section_pages = set()

    # Pattern to match section headers: number followed by any text
    # Capitalization-agnostic, accepts any punctuation or none
    section_header_pattern = re.compile(r'^\s*(\d+(?:\.\d+)+)\s+(.+?)\s*$')

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Find horizontal rule that separates main text from footnotes
            footnote_separator_y = _find_footnote_separator(page)

            # Extract text, cropping to exclude footnotes if separator found
            if footnote_separator_y is not None:
                # Crop page to above separator
                bbox = (0, 0, page.width, footnote_separator_y)
                cropped = page.crop(bbox)
                text = cropped.extract_text()
            else:
                # No separator found, use full page
                text = page.extract_text()

            if not text:
                continue

            lines = text.split('\n')

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                # Check if this line starts a section header
                match = section_header_pattern.match(line)
                if match:
                    # Save previous section if exists
                    if current_section_id:
                        sections[current_section_id] = {
                            'title': current_section_title,
                            'text': '\n'.join(current_section_text).strip(),
                            'page_numbers': sorted(list(current_section_pages))
                        }

                    # Start new section
                    current_section_id = match.group(1)
                    title = match.group(2).strip()

                    # Determine section depth (count dots)
                    section_depth = current_section_id.count('.')

                    # Level 3+ sections (e.g., 5.5.1): multi-line, period-terminated
                    # Level 2 sections (e.g., 5.5): single-line, all caps, no period
                    if section_depth >= 2:
                        # Check if next line is title continuation
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if next_line and not section_header_pattern.match(next_line):
                                # If next line has a period, split on it
                                if '.' in next_line:
                                    period_idx = next_line.index('.')
                                    title = title + ' ' + next_line[:period_idx + 1]
                                    # Put the remainder back for processing as section text
                                    remainder = next_line[period_idx + 1:].strip()
                                    if remainder:
                                        lines[i + 1] = remainder
                                        # Don't increment i - let outer loop process the remainder
                                    else:
                                        i += 1  # Skip empty line after period
                                else:
                                    # No period, just append whole line
                                    title = title + ' ' + next_line
                                    i += 1  # Move past the line we consumed

                    # Remove trailing period if present
                    current_section_title = title.rstrip('.')
                    current_section_text = []
                    current_section_pages = {page_num}
                else:
                    # Add to current section text
                    if current_section_id:
                        current_section_text.append(line)
                        current_section_pages.add(page_num)

                i += 1

        # Save last section
        if current_section_id:
            sections[current_section_id] = {
                'title': current_section_title,
                'text': '\n'.join(current_section_text).strip(),
                'page_numbers': sorted(list(current_section_pages))
            }

    # Filter sections by prefix if specified
    if section_prefix:
        sections = {
            section_id: section_data
            for section_id, section_data in sections.items()
            if section_id == section_prefix or section_id.startswith(section_prefix + '.')
        }

    # Add parent-child relationships
    sections = _add_hierarchy(sections)

    return sections


def _find_footnote_separator(page) -> Optional[float]:
    """
    Find the horizontal rule that separates main text from footnotes.

    Returns the Y-coordinate of the separator, or None if not found.
    The footnote separator is consistently 140px wide across all pages.
    """
    # Look for thin horizontal rectangles (the separator line)
    rects = page.rects
    if not rects:
        return None

    # The footnote separator is exactly 140px wide on every page
    # (wider lines are underlines/decorations)
    for rect in rects:
        is_thin = rect['height'] < 5
        is_black = rect.get('non_stroking_color', rect.get('stroking_color')) == 0
        is_footnote_separator = abs(rect['width'] - 140.0) < 1  # 140px ±1px tolerance

        if is_thin and is_black and is_footnote_separator:
            # Found the footnote separator
            return rect['top']

    return None




def _add_hierarchy(sections: Dict) -> Dict:
    """Add parent and children fields to create hierarchy."""
    for section_id in sections.keys():
        # Determine parent (e.g., "5.5.1.1" -> parent is "5.5.1")
        parts = section_id.split('.')
        if len(parts) > 2:  # Has a parent beyond root
            parent_id = '.'.join(parts[:-1])
            sections[section_id]['parent'] = parent_id
        elif len(parts) == 2:
            # Top level section like "5.5"
            sections[section_id]['parent'] = parts[0]

        # Find children
        children = []
        for other_id in sections.keys():
            other_parts = other_id.split('.')
            # Check if other_id is a direct child
            if len(other_parts) == len(parts) + 1 and other_id.startswith(section_id + '.'):
                children.append(other_id)

        sections[section_id]['children'] = sorted(children)

    return sections


def extract_rules(sections: Dict, section_id: str, openai_client) -> List[Dict]:
    """
    Extract legal rules from a section using GPT.
    Will be implemented in Phase 2.
    """
    # Placeholder for Phase 2
    raise NotImplementedError("Rule extraction will be implemented in Phase 2")
