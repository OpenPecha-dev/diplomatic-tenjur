# coding='utf-8'

"""
Pedurma footnotes Reconstruction
footnotes reconstruction script for the ocred katen pedurma using annotation transfer with
google's dmp.(https://github.com/google/diff-match-patch)
This script allows to transfer a specific set of annotations(footnotes and footnotes markers)
from text A(OCRed etext) to text B(clean etext). We first compute a diff between  texts
A and B, then filter the annotations(dmp diffs) we want to transfer and then apply them to
text B.
"""
import re
from collections import defaultdict
from itertools import zip_longest
from pathlib import Path

import yaml
from antx import transfer

from pedurma.preprocess import (
    preprocess_google_notes,
    preprocess_namsel_notes,
)
from pedurma.utils import optimized_diff_match_patch


def rm_google_ocr_header(text):
    """Remove header of google ocr.

    Args:
        text (str): google ocr

    Returns:
        str: header removed
    """
    header_pattern = (
        "\n\n\n\n{1,18}.+\n(.{1,30}\n)?(.{1,15}\n)?(.{1,15}\n)?(.{1,15}\n)?"
    )
    result = re.sub(header_pattern, "\n\n\n", text)
    return result


def get_diffs(text1, text2):
    """Compute diff between source and target with DMP.

    Args:
        source (str): source text
        target (str): target text
        optimized (bool): whether to use optimized dmp with node.
    Returns:
        list: list of diffs
    """
    print("[INFO] Computing diffs ...")
    dmp = optimized_diff_match_patch()
    diffs = dmp.diff_main(text1, text2)
    print("[INFO] Diff computed!")
    return diffs


# HACK is that useful?


def rm_noise(diff):
    """Filter out noise from diff text.

    Args:
        diff (str): diff text
    Returns:
        str: cleaned diff text
    """
    result = diff
    patterns = ["\n", "\u0020+", "་+?"]
    for pattern in patterns:
        noise = re.search(pattern, diff)
        if noise:
            result = result.replace(noise[0], "")
    return result


def rm_markers_ann(text):
    """Remove page annotation and replace footnotesmarker with #.

    Args:
        text (str): diff applied text

    Returns:
        str: diff applied text without page annotation and replaced footnotesmarker with #
    """
    result = ""
    lines = text.splitlines()
    for line in lines:
        line = re.sub("<p.+?>", "", line)
        line = re.sub("<.+?>", "#", line)
        result += line + "\n"
    return result


def get_pg_ann(diff, vol_num):
    """Extract pedurma page and put page annotation.

    Args:
        diff (str): diff text
        vol_num (int): volume number

    Returns:
        str: page annotation
    """
    pg_no_pattern = fr"{vol_num}\S*?(\d+)"
    pg_pat = re.search(pg_no_pattern, diff)
    pg_num = pg_pat.group(1)
    return f"<p{vol_num}-{pg_num}>"


def get_abs_marker(diff):
    """Extract absolute footnotes marker from diff text.

    Args:
        diff (str): diff text

    Returns:
        str: footnotes marker
    """
    marker_ = ""
    patterns = ["[①-⓪]+", "[༠-༩]+", "[0-9]+"]
    for pattern in patterns:
        if re.search(pattern, diff):
            marker = re.search(pattern, diff)
            marker_ += marker[0]
    return marker_


def get_excep_marker(diff):
    """Check is diff belong to exception marker or not if so returns it.

    Args:
        diff (str): diff text

    Returns:
        str: exception marker
    """
    marker_ = ""
    patterns = ["<m(.+?)>", "(.*#.*)"]
    for pattern in patterns:
        marker = re.search(pattern, diff)
        if re.search(pattern, diff):
            marker = re.search(pattern, diff)
            marker_ = marker.group(1)
    return marker_


def is_punct(char):
    """Check whether char is tibetan punctuation or not.

    Args:
        diff (str): character from diff

    Returns:
        flag: true if char is punctuation false if not
    """
    if char in ["་", "།", "༔", ":", "། །", "༄", "༅"]:
        return True
    else:
        return False


def isvowel(char):
    """Check whether char is tibetan vowel or not.

    Args:
        char (str): char to be checked

    Returns:
        boolean: true for vowel and false for otherwise
    """
    flag = False
    vowels = ["\u0F74", "\u0F72", "\u0F7A", "\u0F7C"]
    for pattern in vowels:
        if re.search(pattern, char):
            flag = True
    return flag


def is_midsyl(left_diff, right_diff):
    """Check if current diff is mid syllabus.

    Args:
        left_diff (str): left diff text
        right_diff (str): right diff text

    Returns:
        boolean : True if it is mid syllabus else False
    """
    if left_diff:
        right_diff_text = right_diff.replace("\n", "")
        left_diff_text = left_diff.replace("\n", "")
        if not right_diff_text or not left_diff_text:
            return False
        if not is_punct(left_diff_text[-1]) and not is_punct(right_diff_text[0]):
            return True
    return False


def double_mid_syl_marker(result):
    """Handle the consecutive marker occurance in body text.

    Args:
        result (list): filtered diffs

    Returns:
        Boolean: True if double consecutive marker detected in case of mid syl esle false
    """
    i = -1
    while abs(i)<len(result) and not is_punct(result[i][1]):
        if result[i][2] == "marker":
            return False
        else:
            i -= 1
    return True


def handle_mid_syl(
    result, diffs, left_diff, i, diff, right_diff_text, marker_type=None
):
    """Handle the middle of syllabus diff text in different situation.

    Args:
        result (list): Filtered diff list
        diffs (list): Unfilterd diff list
        left_diff (list): left diff type and text from current diff
        diff (list): current diff type and text
        i (int): current diff index
        right_diff (list): right diff type and text from current diff
        marker_type (str): marker type can be marker or candidate marker
    """
    # make it marker if marker found  (revision)
    if double_mid_syl_marker(result):
        diff_ = rm_noise(diff[1])
        if left_diff[1][-1] == " ":
            lasttwo = left_diff[1][-2:]
            result[-1][1] = result[-1][1][:-2]
            result.append([1, diff_, f"{marker_type}"])
            diffs[i + 1][1] = lasttwo + diffs[i + 1][1]
        elif right_diff_text[0] == " ":
            result.append([1, diff_, f"{marker_type}"])
        elif isvowel(left_diff[1][-1]):
            syls = re.split("(་|།)", right_diff_text)
            first_syl = syls[0]
            result[-1][1] += first_syl
            diffs[i + 1][1] = diffs[i + 1][1][len(first_syl) :]
            result.append([1, diff_, f"{marker_type}"])
        else:
            if isvowel(right_diff_text[0]):
                syls = re.split("(་|།)", right_diff_text)
                first_syl = syls[0]
                result[-1][1] += first_syl
                diffs[i + 1][1] = diffs[i + 1][1][len(first_syl) :]
                result.append([1, diff_, f"{marker_type}"])
            else:
                if left_diff[0] != (0 or 1):
                    lastsyl = left_diff[1].split("་")[-1]
                    result[-1][1] = result[-1][1][: -len(lastsyl)]
                    result.append([1, diff_, f"{marker_type}"])
                    diffs[i + 1][1] = lastsyl + diffs[i + 1][1]


def tseg_shifter(result, diffs, left_diff_text, i, right_diff_text):
    """Shift tseg if right diff starts with one and left diff ends with non punct.

    Args:
        result (list): filtered diff
        diffs (list): unfiltered diffs
        left_diff (list): contains left diff type and text
        i (int): current index if diff in diffs
        right_diff (list): contains right diff type and text
    """
    if right_diff_text[0] == "་" and not is_punct(left_diff_text):
        result[-1][1] += "་"
        diffs[i + 1][1] = diffs[i + 1][1][1:]


def get_marker(diff):
    """Extarct marker from diff text.

    Args:
        diff (str): diff text

    Returns:
        str: marker
    """
    if get_abs_marker(diff):
        marker = get_abs_marker(diff)
        return marker
    elif get_excep_marker(diff):
        marker = get_excep_marker(diff)
        return marker
    else:
        return ""


def is_circle_number(footnotes_marker):
    """Check whether footnotes marker is number in circle or not and if so
       returns equivalent number.

    Args:
        footnotes_marker (str): footnotes marker
    Returns:
        str: number inside the circle
    """
    value = ""
    number = re.search("[①-⓪]", footnotes_marker)
    if number:
        circle_num = {
            "⓪": "0",
            "①": "1",
            "②": "2",
            "③": "3",
            "④": "4",
            "⑤": "5",
            "⑥": "6",
            "⑦": "7",
            "⑧": "8",
            "⑨": "9",
            "⑩": "10",
            "⑪": "11",
            "⑫": "12",
            "⑬": "13",
            "⑭": "14",
            "⑮": "15",
            "⑯": "16",
            "⑰": "17",
            "⑱": "18",
            "⑲": "19",
            "⑳": "20",
        }
        value = circle_num.get(number[0])
    return value


def translate_tib_number(footnotes_marker):
    """Translate tibetan numeral in footnotes marker to roman number.

    Args:
        footnotes_marker (str): footnotes marker
    Returns:
        str: footnotes marker having numbers in roman numeral
    """
    value = ""
    if re.search(r"\d+\S+(\d+)", footnotes_marker):
        return value
    tib_num = {
        "༠": "0",
        "༡": "1",
        "༢": "2",
        "༣": "3",
        "༤": "4",
        "༥": "5",
        "༦": "6",
        "༧": "7",
        "༨": "8",
        "༩": "9",
    }
    numbers = re.finditer(r"\d", footnotes_marker)
    if numbers:
        for number in numbers:
            if re.search(r"[༠-༩]", number[0]):
                value += tib_num.get(number[0])
            else:
                value += number[0]
    return value


def get_value(footnotes_marker):
    """Compute the equivalent numbers in footnotes marker payload and return it.

    Args:
        footnotes_marker (str): footnotes marker
    Returns:
        str: numbers in footnotes marker
    """
    value = ""
    if is_circle_number(footnotes_marker):
        value = is_circle_number(footnotes_marker)
        return value
    elif translate_tib_number(footnotes_marker):
        value = translate_tib_number(footnotes_marker)
        return value
    return value


def format_diff(filter_diffs, vol_num, type_=None):
    """Format list of diff on target text.

    Args:
        diffs (list): list of diffs
        image_info (list): contains work_id, volume number and image source offset
        type_ (str): diff type can be footnotes or body
    Returns:
        str: target text with transfered annotations with markers.
    """
    diffs = filter_diffs
    vol_num = vol_num
    result = ""
    for diff_type, diff_text, diff_tag in diffs:
        if diff_type == 1 or diff_type == 0:
            if diff_tag:
                if diff_tag == "pedurma-page":
                    result += get_pg_ann(diff_text, vol_num)
                if diff_tag == "marker":
                    if get_abs_marker(diff_text):
                        marker = get_abs_marker(diff_text)
                        value = get_value(marker)
                        result += f"<{value},{marker}>"
                    elif get_excep_marker(diff_text):
                        marker = get_excep_marker(diff_text)
                        result += f"<{marker}>"
                    else:
                        result += f"<{diff_text}>"
                elif diff_tag == "pg_ref":
                    result += diff_text
            else:
                result += diff_text

    return result


def reformatting_body(text):
    """Reformat marker annotation using pedurma page.

    Args:
        text (str): unformatted text

    Returns:
        str: formatted text
    """
    result = ""
    page_anns = re.findall(r"<p\S+?>", text)
    pages = re.split(r"<p\S+?>", text)
    for page, ann in zip_longest(pages, page_anns, fillvalue=""):
        markers = re.finditer("<.+?>", page)
        for i, marker in enumerate(markers, 1):
            repl = f"<{i},{marker[0][1:-1]}>"
            page = page.replace(marker[0], repl, 1)
        result += page + ann
    return result


def rm_marker(diff):
    """Remove marker of google ocr text.

    Args:
        diff (str): diff text

    Returns:
        str: diff text without footnotes marker of google ocr
    """
    result = diff
    patterns = [
        r"©",
        r"®",
        r"\“",
        r"•",
        r"[༠-༩]",
        r"[a-zA-Z]",
        r"\)",
        r"\(",
        r"\u0020+",
        r"@",
        r"་+?",
        r"། །",
        r"\d",
        r"།",
        r"༄༅",
    ]
    for pattern in patterns:
        if re.search(pattern, diff):
            result = re.sub(pattern, "", result)
    return result


def is_note(diff):
    """Check if diff text is note or marker.

    Args:
        diff (str): diff text

    Returns:
        boolean: True if diff text is note else False.
    """
    flag = True
    patterns = [r"[①-⑳]", r"[༠-༩]", r"\)", r"\(", r"\d", r"⓪"]
    for pattern in patterns:
        if re.search(pattern, diff):
            flag = False
    return flag


def parse_pg_ref_diff(diff, result):
    """Parse page ref and marker if both exist in one diff.

    Args:
        diff (str): diff text
        result (list): filtered diff
    """
    lines = diff.splitlines()
    for line in lines:
        if line:
            if re.search("<r.+?>", line):
                result.append([1, line, "page_ref"])
            elif re.search("(<m.+?>)(.+)", line):
                marker = re.search("(<m.+?>)(.+)", line)
                result.append([1, marker.group(1), "marker"])
                result.append([1, marker.group(2), ""])
            elif re.search("<m.+?>", line):
                marker = re.search("<m.+?>", line)
                result.append([1, marker[0], "marker"])


def double_marker_handler(result):
    if len(result) > 3:
        prev2 = result[-3]
        prev1 = result[-2]
        cur = result[-1]
        if cur[2] == "marker":
            if prev2[2] == "marker" and prev1[1] in ["\n", " ", "", "།"]:
                del result[-1]
    else:
        pass


def reformat_footnotes(text):
    """Replace edition name with their respective unique id and brings every footnotes to newline.
    Args:
        text (str): google OCRed footnotes with namsel footnotes markers transfered.
    Returns:
        (str): reformatted footnote
    """
    text = text.replace("\n", "")
    text = re.sub("(<+)", r"\n\1", text)
    result = demultiply_diffs(text)

    return result


def filter_diffs(diffs_list, type, vol_num):
    """Filter diff of text A and text B.

    Args:
        diffs_list (list): list of diffs
        type (str): type of text
        image_info (list): contains work_id, volume number and source image offset.

    Returns:
        list: filtered diff
    """
    left_diff = [0, ""]
    result = []
    vol_num = vol_num
    diffs = diffs_list
    for i, diff in enumerate(diffs):
        diff_type, diff_text = diff
        if diff_type == 0:  # in both
            if re.search(
                fr"{vol_num}་?\D་?\d+", diff_text
            ):  # checking diff text is page or not
                result.append([0, diff_text, "pedurma-page"])
            else:
                result.append([diff_type, diff_text, ""])

        elif diff_type == 1:  # in target
            result.append([diff_type, diff_text, ""])
        elif diff_type == -1:  # in source

            if re.search(
                fr"{vol_num}་?\D་?\d+", diff_text
            ):  # checking diff text is page or not
                result.append([1, diff_text, "pedurma-page"])
            else:

                if i > 0:  # extracting left context of current diff
                    left_diff = diffs[i - 1]
                left_diff_type, left_diff_text = left_diff
                if i < len(diffs) - 1:  # extracting right context of current diff
                    right_diff = diffs[i + 1]
                right_diff_type, right_diff_text = right_diff
                diff_ = rm_noise(
                    diff_text
                )  # removes unwanted new line, space and punct
                if left_diff_type == 0 and right_diff_type == 0:
                    # checks if current diff text is located in middle of a syllable
                    if is_midsyl(left_diff_text, right_diff_text) and get_marker(
                        diff_text
                    ):
                        handle_mid_syl(
                            result,
                            diffs,
                            left_diff,
                            i,
                            diff,
                            right_diff_text,
                            marker_type="marker",
                        )
                    # checks if current diff text contains absolute marker or not
                    elif get_marker(diff_text):
                        # Since cur diff is not mid syl, hence if any right diff starts with tseg will
                        # be shift to left last as there are no marker before tseg.
                        tseg_shifter(result, diffs, left_diff_text, i, right_diff_text)
                        result.append([1, diff_, "marker"])
                    # Since diff type of -1 is from namsel and till now we are not able to detect
                    # marker from cur diff, we will consider it as candidate marker.
                    elif diff_:
                        if (
                            "ང" in left_diff_text[-3:]
                            and diff_ == "སྐེ"
                            or diff_ == "ུ"
                        ):  # an exception case where candidate fails to be marker.
                            continue
                        # print(diffs.index(right_diff), right_diff)
                        elif is_midsyl(left_diff_text, right_diff_text):
                            handle_mid_syl(
                                result,
                                diffs,
                                left_diff,
                                i,
                                diff,
                                right_diff_text,
                                marker_type="marker",
                            )

                        else:
                            tseg_shifter(
                                result, diffs, left_diff_text, i, right_diff_text
                            )
                            result.append([1, diff_, "marker"])
                elif right_diff_type == 1:
                    # Check if current diff is located in middle of syllabus or not.
                    if is_midsyl(left_diff_text, right_diff_text) and get_marker(
                        diff_text
                    ):
                        handle_mid_syl(
                            result,
                            diffs,
                            left_diff,
                            i,
                            diff,
                            right_diff_text,
                            marker_type="marker",
                        )
                    elif get_marker(diff_text):
                        # Since cur diff is not mid syl, hence if any right diff starts with tseg will
                        # be shift to left last as there are no marker before tseg.
                        tseg_shifter(result, diffs, left_diff_text, i, right_diff_text)
                        result.append([1, diff_, "marker"])
                        # if "#" in right_diff[1]:
                        #     diffs[i + 1][1] = diffs[i + 1][1].replace("#", "")
                    else:
                        if diff_ != "" and right_diff_text in ["\n", " ", "་"]:
                            if (
                                "ང" in left_diff_text[-2:] and diff_ == "སྐེ"
                            ):  # an exception case where candidate fails to be marker.
                                continue
                            elif is_midsyl(left_diff_text, right_diff_text):
                                handle_mid_syl(
                                    result,
                                    diffs,
                                    left_diff,
                                    i,
                                    diff,
                                    right_diff_text,
                                    marker_type="marker",
                                )
                            else:
                                tseg_shifter(
                                    result, diffs, left_diff_text, i, right_diff_text
                                )
                                result.append([1, diff_, "marker"])
                                # if "#" in right_diff[1]:
                                #     diffs[i + 1][1] = diffs[i + 1][1].replace("#", "")
                    # if diff_ is not empty and right diff is ['\n', ' '] then make it candidate markrer
                double_marker_handler(result)

    filter_diffs = result

    return filter_diffs


def filter_footnotes_diffs(diffs_list, vol_num):
    """Filter the diffs of google ocr output and namsel ocr output.

    Args:
        diffs (list): diff list
        vol_num (int): colume number

    Returns:
        list: filtered diff containing notes from google ocr o/p and marker from namsel ocr o/p
    """
    diffs = diffs_list
    left_diff = [0, "", ""]
    filtered_diffs = []
    for i, diff in enumerate(diffs):
        diff_type, diff_text, diff_tag = diff
        if diff_type == 0:
            filtered_diffs.append(diff)
        elif diff_type == 1:
            if i > 0:  # extracting left context of current diff
                left_diff = diffs[i - 1]
            if i < len(diffs) - 1:  # extracting right context of current diff
                right_diff = diffs[i + 1]
            left_diff_tag = left_diff[2]
            if left_diff_tag != "marker" and left_diff_tag != "pedurma-page":
                if "4" in diff_text:
                    right_diff_text = rm_noise(right_diff[1])
                    if re.search(r"\d{2}", diff_text) or not right_diff_text:
                        continue
                    clean_diff = re.sub("[^4|\n]", "", diff_text)
                    filtered_diffs.append([0, clean_diff, "marker"])
                else:
                    diff_text = rm_marker(diff_text)
                    filtered_diffs.append(diff)
        else:
            filtered_diffs.append(diff)

    return filtered_diffs


def postprocess_footnotes(footnotes, vol_num):
    """Save the formatted footnotes to dictionary with key as page ref and value as footnotes in that page.
    Args:
        footnotes (str): formatted footnote
    Returns:
        dict: key as page ref and value as footnotes in that page
    """
    footnote_result = {}
    page_refs = re.findall("<r.+?>", footnotes)
    pages = re.split("<r.+?>", footnotes)[1:]

    first_ref = page_refs[0]
    table = first_ref.maketrans("༡༢༣༤༥༦༧༨༩༠", "1234567890", "<r>")
    start = int(first_ref.translate(table))
    print(
        f"number of page ref found -{len(page_refs)} number of page found-{len(pages)}"
    )
    for walker, (page, page_ref) in enumerate(
        zip_longest(pages, page_refs, fillvalue=""), start
    ):
        markers = re.finditer("<.+?>", page)
        marker_l = []
        for i, marker in enumerate(markers, 1):
            repl = f"<{i},{marker[0][1:-1]}>"
            page = page.replace(marker[0], repl, 1)
        marker_list = [footnotes.strip() for footnotes in page.splitlines()]
        # Removes the noise marker without footnote
        for marker in marker_list:
            if marker:
                if re.search("<.+?>(.+?)", marker):
                    marker_l.append(marker)
                else:
                    if "<" not in marker:
                        marker_l.append(marker)
        footnote_result[walker] = marker_l
    return footnote_result


def demultiply_diffs(text):
    """ '<12,⓪⓪>note' --> '<12,⓪>note\n<12,⓪>note'
    Arguments:
        text {str} -- [description]

    Returns:
        str -- [description]
    """
    patterns = [
        [
            r"(\n<\d+,)([①-⓪])([①-⓪])([①-⓪])([①-⓪])([①-⓪])(>.+)",
            r"\g<1>\g<2>\g<7>\g<1>\g<3>\g<7>\g<1>\g<4>\g<7>\g<1>\g<5>\g<7>\g<1>\g<6>\g<7>",
        ],
        [r"(\n<m)([①-⑨])([①-⑨])(>.+)", r"\g<1>\g<2>\g<4>\g<1>\g<3>\g<4>"],
        [
            r"(\n<\d+,)([①-⓪])([①-⓪])([①-⓪])([①-⓪])(>.+)",
            r"\g<1>\g<2>\g<6>\g<1>\g<3>\g<6>\g<1>\g<4>\g<6>\g<1>\g<5>\g<6>",
        ],
        [
            r"(\n<\d+,)([①-⓪])([①-⓪])([①-⓪])(>.+)",
            r"\g<1>\g<2>\g<5>\g<1>\g<3>\g<5>\g<1>\g<4>\g<5>",
        ],
        [r"(\n<\d+,)([①-⓪])([①-⓪])(>.+)", r"\g<1>\g<2>\g<4>\g<1>\g<3>\g<4>"],
    ]
    for p in patterns:
        text = re.sub(p[0], p[1], text)
    return text


def merge_footnotes_per_page(page, foot_notes):
    """Merge the footnote of a certain page to its body text.

    Args:
        page (str): content in page
        foot_notes (list): list of footnotes

    Returns:
        str: content of page attached with their footnote adjacent to their marker
    """
    with_marker = page
    without_marker = page
    markers = re.finditer("<.+?>", page)
    for i, (marker, foot_note) in enumerate(zip(markers, foot_notes)):
        if re.search("<p.+>", marker[0]):
            repl1 = marker[0]
            repl2 = marker[0]
        else:
            marker_parts = marker[0][1:-1].split(",")
            body_incremental = marker_parts[0]
            body_value = marker_parts[1]
            footnotes_parts = foot_note.split(">")
            footnotes_incremental = footnotes_parts[0].split(",")[0][1:]
            try:
                footnotes_value = footnotes_parts[0].split(",")[1]
            except Exception:
                footnotes_value = ""
            try:
                note = footnotes_parts[1]
            except Exception:
                note = ""

            repl1 = f"<{body_incremental},{body_value};{footnotes_incremental},{footnotes_value},{note}>"
            repl2 = f"<{note}>"
        with_marker = with_marker.replace(marker[0], repl1, 1)
        without_marker = without_marker.replace(marker[0], repl2, 1)
    result_with_marker = with_marker
    result_without_marker = without_marker
    return result_with_marker, result_without_marker


def reconstruct_body(source, target, vol_num):
    namsel_text = source
    google_text = target
    print("Calculating diffs...")
    diffs = get_diffs(namsel_text, google_text)
    diffs_list = list(map(list, diffs))
    print("Filtering diffs...")
    filtered_diffs = filter_diffs(diffs_list, "body", vol_num)
    new_text = format_diff(filtered_diffs, vol_num, type_="body")
    new_text = reformatting_body(new_text)
    return new_text


def get_clean_google_durchen(google_footnote):
    google_footnote = rm_google_ocr_header(google_footnote)
    clean_google_footnote = preprocess_google_notes(google_footnote)
    return clean_google_footnote


def get_clean_namsel_durchen(namsel_footnote):
    clean_namsel_footnote = preprocess_namsel_notes(namsel_footnote)
    return clean_namsel_footnote


def reconstruct_footnote(namsel_footnote, google_footnote, vol_num):
    clean_google_footnote = get_clean_google_durchen(google_footnote)
    clean_namsel_footnote = get_clean_namsel_durchen(namsel_footnote)
    annotations = [
        ["marker", "(<m.+?>)"],
        ["marker", "([①-⑩])"],
        ["pg_ref", "(<r.+?>)"],
        ["pedurma-page", "(<p.+?>)"],
    ]
    print("Calculating diffs..")
    diffs = transfer(clean_namsel_footnote, annotations, clean_google_footnote, output="diff")
    diffs_list = list(map(list, diffs))
    filtered_diffs = filter_footnotes_diffs(diffs_list, vol_num)
    new_text = format_diff(filtered_diffs, vol_num, type_="footnotes")
    reformatted_footnotes = reformat_footnotes(new_text)
    formatted_footnotes = postprocess_footnotes(reformatted_footnotes, vol_num)
    return formatted_footnotes


def get_whole(pagewise_text_durchen, type):
    result = ""
    pagewise = pagewise_text_durchen[type]
    for pg_ann, pg_content in pagewise.items():
        result += f"[{pg_ann}]\n{pg_content['pg_content']}"
    return result


def get_page_index(pg_num):
    pg_index = ""
    if pg_num % 2 == 0:
        pg_index = f"{pg_num/2}b"
    else:
        pg_index = f"{pg_num/2+1}a"
    return pg_index


def get_page_num(body_text, vol_num):
    vol = vol_num
    pg_pat = re.search(fr"<p{vol}-(\d+)>", body_text)
    pg_num = int(pg_pat.group(1))
    return pg_num

def get_preview_page(g_body_page, n_body_page, g_durchen_page, n_durchen_page):
    g_body_page_content = g_body_page.content
    n_body_page_content = n_body_page.content
    g_durchen_page_content = g_durchen_page.content
    n_durchen_page_content = n_durchen_page.content
    vol_num = g_body_page.vol
    n_body_page_content = transfer(
        g_body_page_content, [["pedurma", "(#)"]], n_body_page_content, output="txt"
    )
    g_body_page_content = g_body_page_content.replace("#", "")
    body_result = reconstruct_body(n_body_page_content, g_body_page_content, vol_num)
    footnotes = reconstruct_footnote(
        n_durchen_page_content, g_durchen_page_content, vol_num
    )
    pg_num = get_page_num(body_result, vol_num)
    merge_marker, merge = merge_footnotes_per_page(body_result, footnotes[pg_num])
    return merge
