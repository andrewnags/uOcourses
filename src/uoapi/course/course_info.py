import sys

from bs4 import BeautifulSoup
from typing import (
    Callable,
    List,
    TypeVar,
    cast
)

import requests
import regex as re

from uoapi.course import patterns as pt
from uoapi.course import Prereq

try:
    from re import (
        Match
    )
except ImportError:
    # https://github.com/python/cpython/blob/4bb332cfd1f9740b1e31d2d8b8bf1bedca3439ff/Lib/re.py#L272
    import sre_compile as _sre
    Match = type(_sre.compile('', 0).match(''))

# requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':DES-CBC3-SHA'
# timetable_url = 'https://web30.uottawa.ca/v3/SITS/timetable/Search.aspx'

# Course Info Parameters
course_url = 'https://catalogue.uottawa.ca/en/courses/'

T = TypeVar('T')

#############################################################################
# COURSE INFO SCRAPING
#############################################################################


def _extract_codes(string: str) -> List[str]:
    '''
    Returns course codes found in string;
    if multiple codes are found and return_all is False, then returns an invalid code
    Used in get_subjects.ipynb '''
    return __perform_extraction(
        string,
        extracting_fn=lambda x: x.group(0),
        validating_fn=lambda x: return_all or len(x) == 1,
        default='XXX 0000'
    )


def _extract_credits(string: str) -> List[int]:
    '''
    Searches string for a number of credits/units
    (Assuming the string is the title of a course)
    Used in get_subjects.ipynb
    '''
    return __perform_extraction(
        string,
        extracting_fn=lambda x: int(
            cast(str, x.group(0))
            .split(' ')[0]
            .strip('(')
        ),
        validating_fn=lambda x: len(x) == 1,
        default=[0]
    )


def __perform_extraction(
    string: str,
    extracting_fn: Callable[[Match], T],
    validating_fn: Callable[[List[T]], bool],
    default: T,
):
    ret = list({
        extracting_fn(x)
        for x in re.finditer(pt.credit_re, string)
    })

    if validating_fn(ret):
        return ret

    return [default]


def scrape_subjects(url: str = course_url):
    '''
    Scrapes the list of subjects with links to their respective
    course catalogues from the uOttawa website
    () -> pandas DataFrame with columns: Subject, Code, Link
    Used in get_subjects.ipynb
    '''
    page = requests.get(url).text

    soup = BeautifulSoup(page, 'html.parser')
    content = soup.find('div', attrs={'class': 'az_sitemap'})
    subj_tags = content.find_all('a', attrs={'href': pt.href_re})

    subj_table = [[tag.string, tag['href'].strip('/').rsplit('/')[-1].strip().strip("/")]
                  for tag in subj_tags]
    return [{
        "subject": pt.subj_re.sub("", x[0]).strip(),
        "subject_code": x[1].upper(),
        "link": url + x[1] + "/",
    } for x in subj_table]


# @TODO break up into subfunctions
def get_courses(link):
    '''
    Scrapes the page given by link for courses and their
    descriptions, components, prerequisites, etc.
    '''
    raw_courses = BeautifulSoup(requests.get(link).text, 'html.parser')
    raw_courses = raw_courses.find_all('div', attrs={'class': 'courseblock'})
    desc = ''
    for course in raw_courses:
        try:
            title: str = (
                course.find('p', attrs={'class': 'courseblocktitle'})
                .text
                .replace('\xa0', ' ')
                .strip()
            )
            title = title.replace("&nbsp;", " ").strip()
        except AttributeError as e:
            print(course, file=sys.stderr)
            raise e
        else:
            code = _extract_codes(title, False)[0]
            credits = _extract_credits(title)[0]
            title = re.sub(pt.code_re, '', title)
            title = re.sub(pt.credit_re, '', title).strip()
        try:
            desc = course.find('p', attrs={'class': 'courseblockdesc'})
            desc = desc.text.replace('\xa0', ' ').strip()
        except AttributeError as e:
            if desc is None:
                desc = ''
            else:
                print(course)
                raise e
        # parsing the course component and prerequisite info
        # from the courseblockextra and distinguishing them
        blocks = []
        for block in course.find_all('p', attrs={'class': 'courseblockextra'}):
            try:
                block = block.text.replace('\xa0', ' ').strip().strip('.')
                block = block.replace("&nbsp;", " ").strip().strip('.')
                blocks.append(block)
            except AttributeError as e:
                print(course)
                print(block)
                raise e
        if len(blocks) == 0:
            comp = ''
            pre = ''
        elif len(blocks) == 1:
            if ("Volet" in blocks[0]) or ("Course Component" in blocks[0]):
                comp = blocks[0]
                pre = ''
            elif ("Préalable" in blocks[0]) or ("Prerequisite" in blocks[0]):
                comp = ''
                pre = blocks[0]
            else:
                comp = ''
                pre = ''
        elif len(blocks) == 2:
            cond_comp0 = ("Volet" in blocks[0]) or ("Course Component" in blocks[0])
            cond_pre1 = ("Préalable" in blocks[1]) or ("Prerequisite" in blocks[1])
            cond_comp1 = ("Volet" in blocks[1]) or ("Course Component" in blocks[1])
            cond_pre0 = ("Préalable" in blocks[0]) or ("Prerequisite" in blocks[0])
            if cond_comp0 and not cond_pre0:
                comp = blocks[0]
            elif cond_comp1 and not cond_pre1:
                comp = blocks[1]
            else:
                comp = ''
            if cond_pre0 and not cond_comp0:
                pre = blocks[0]
            elif cond_pre1 and not cond_comp1:
                pre = blocks[1]
            else:
                pre = ''
        else:
            comp = ''
            pre = ''
        # adding component info to the end of the description
        desc = desc + '\n' + comp
        desc = desc.strip()
        # getting the components from after the colon in the sentence
        comp = comp.split(':', 1)[-1].strip()
        comp = [x.strip().upper() for x in comp.split('/')[-1].split(',')]
        # getting the prerequisites from after the colon in the sentence
        prereqs = Prereq(pre)
        dep = prereqs.prereqs
        parse_status = prereqs.parse_status
        pre = pre.split(':', 1)[-1].strip()
        # TODO: ideally we would like to save the whole Prereq object
        # to the dataframe, but since it does not output to json,
        # using this in the meantime
        yield {
            "course_code": pt.code_groups.search(code).groups()[1].upper(),
            "title": title,
            "credits": credits,
            "description": desc,
            "components": comp,
            "prerequisites": pre,
            "dependencies": dep,
            "parsing_successful": parse_status
        }
