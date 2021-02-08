import sys
import time
import json

from uoapi.cli_tools import make_parser, make_cli
from uoapi.course import scrape_subjects, get_courses


help = (
    "A tool for querying the subjects available, "
    + "and the courses offered for each subject"
)
description = (
    "By default, lookup the subject table. "
    + "If given the --courses (-c) flag, lookup course information as well. "
    + "Suppress the subjects table with --nosubjects (-s). "
    + "If subject codes are given as command line arguments, "
    + "then only query the courses for those sections."
)
epilog = ""


@make_parser(description=description, epilog=epilog)
def parser(default):
    default.add_argument(
        "-c",
        "--courses",
        action="store_true",
        default=False,
        help="query for course information as well",
    )
    default.add_argument(
        "-s",
        "--nosubjects",
        action="store_true",
        default=False,
        help="suppress output of subjects table",
    )
    default.add_argument(
        "subjects",
        action="store",
        metavar="XXX",
        nargs="*",
        help=(
            "list of subjects to query courses "
            + "(if not provided, all subjects will be queried)"
        ),
    )
    default.add_argument(
        "-w",
        "--waittime",
        action="store",
        type=float,
        default=0.5,
        help="specify time (in seconds) to wait between requests",
    )
    # default.add_argument("-r", "--retries",
    #    action="store",
    #    type=int,
    #    default=2,
    #    help="how many times to try and connect to the server",
    # )
    return default


@make_cli(parser)
def cli(args=None):
    if args is None:
        print("Did not receive any arguments", file=sys.stderr)
        sys.exit(1)
    for output in main(not args.nosubjects, args.courses, args.subjects, args.waittime):
        print(json.dumps(output))


def main(subjects=True, courses=False, subject_list=None, waittime=0.5):
    subj = scrape_subjects()
    if subjects:
        yield {"subjects": subj}
    if not courses:
        return
    if len(subject_list) == 0:
        subject_list = None
    else:
        subject_list = {x.strip().upper() for x in subject_list}
    subjects = (
        (x["subject_code"], x["link"]) for x in subj
        if subject_list is None or x["subject_code"] in subject_list
    )
    for subj, link in subjects:
        yield {"courses": {"subject_code": subj, "courses": list(get_courses(link))}}
        time.sleep(waittime)


if __name__ == "__main__":
    cli()
