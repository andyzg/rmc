import argparse
import datetime
import glob
import json
import logging
import os
import re
import sys
import time
import traceback
import urllib2

import lxml.html
from lxml.html import soupparser

import rmc.shared.secrets as s
import rmc.shared.constants as c
import rmc.models as m
import mongoengine as me


API_UWATERLOO_V2_URL = 'https://api.uwaterloo.ca/v2'

# TODO(david): Convert this file to use OpenData v2 (v1 is now deprecated and
#     will be retired April 2014).

reload(sys)
sys.setdefaultencoding('utf-8')

errors = []


def html_parse(url, num_tries=5, parsers=[soupparser]):
    # TODO(mack): should also try lxml.html parser since soupparser could also
    # potentially not parse correctly
    #for parser in [soupparser]:
    for parser in parsers:
        tries = 0
        while True:
            try:
                u = urllib2.urlopen(url)
                result = u.read()
                u.close()
                return parser.fromstring(result)
            except:
                tries += 1
                if tries == num_tries:
                    break

                wait = 2 ** (tries + 1)
                error = 'Exception parsing %s. Sleeping for %s secs'.format(
                            url=url, wait=wait)
                errors.append(error)
                print error
                time.sleep(wait)

    return None


# TODO(david): Convert more calls to use opendata API
# TODO(mack): add to text file rather than directly to mongo
def get_departments():
    departments = []

    # Beautifulsoup parser apparently doesn't work while default parser does.
    # Fucking waterloo and their broken markup.
    url = 'http://ugradcalendar.uwaterloo.ca/page/Course-Descriptions-Index'
    tree = html_parse(url, parsers=[lxml.html])

    dep_xpath = './/span[@id="ctl00_contentMain_lblContent"]/table[1]/tbody/tr'
    for e_department in tree.xpath(dep_xpath):
        e_row = e_department.xpath('.//td')
        department_name = e_row[0].text_content().strip()

        if 'Back to top' in department_name:
            continue

        department_id = e_row[1].text_content().lower().strip()
        department_url = 'http://ugradcalendar.uwaterloo.ca/courses/%s' % department_id
        faculty_id = e_row[2].text_content().lower().strip()

        print department_name, department_id, faculty_id, department_url
        departments.append({
            'id': department_id,
            'name': department_name,
            'url': department_url,
            'faculty_id': faculty_id,
        })

    file_name = os.path.join(
        sys.path[0], '%s/ucalendar_departments.txt' % c.DEPARTMENTS_DATA_DIR)
    with open(file_name, 'w') as f:
        json.dump(departments, f)

    print 'found: %d departments' % len(departments)


def get_data_from_url(url, num_tries=5):
    tries = 0
    while True:
        try:
            u = urllib2.urlopen(url)
            result = u.read()
            u.close()
            if result:
                data = json.loads(result)
                return data
            return None
        except:
            tries += 1
            if tries == num_tries:
                break

            wait = 2 ** (tries + 1)
            error = 'Exception for {url}. Sleeping for {wait} secs'.format(
                    url=url, wait=wait)
            errors.append(error)
            print error
            traceback.print_exc(file=sys.stdout)
            time.sleep(wait)

    return None


def file_exists(path):
    try:
        with open(path):
            pass
        return True
    except:
        return False


def get_ucalendar_courses():
    def get_course_info_from_tree(course_tree):
        course_intro = course_tree.xpath('.//tr[1]/td[1]')[0].text_content()
        # Note, this is Waterloo's course id
        course_id = course_tree.xpath('.//tr[1]/td[2]')[0].text_content()
        course_name = course_tree.xpath('.//tr[2]')[0].text_content()
        course_description = course_tree.xpath('.//tr[3]')[0].text_content()
        course_notes = []
        for e in course_tree.xpath('.//tr//i'):
            text_content = e.text_content().strip()
            if text_content:
                course_notes.append(text_content)

        return {
            'intro': course_intro,
            'id': course_id,
            'name': course_name,
            'description': course_description,
            'notes': course_notes,
        }

    curr_dir = os.path.dirname(os.path.realpath(__file__))
    for department in m.Department.objects:
        file_path = os.path.join(curr_dir, '%s/%s.txt' % (
            c.UCALENDAR_COURSES_DATA_DIR, department.id))
        #if file_exists(file_path):
        #    print 'Skipping: %s' % department.id
        #    continue

        dep_url = 'http://ugradcalendar.uwaterloo.ca/courses/%s' % (
                department.id.upper())
        dep_tree = html_parse(dep_url, num_tries=1)
        if dep_tree is None:
            print 'Skipping: %s' % department.id
            continue

        print 'Processing: %s' % department.id

        course_infos = []
        course_trees = dep_tree.xpath('.//center')
        if not course_trees:
            print 'Could not find courses for %' % department.id
        else:
            for course_tree in course_trees:
                course_info = get_course_info_from_tree(course_tree)
                course_infos.append(course_info)

        with open(file_path, 'w') as f:
            json.dump(course_infos, f)


def get_uwdata_courses():
    api_keys = [
        '66e3d70ec73751bc2c97e5ed0928d540',
        '29d72333db3101ba4116f8f53a43ec1a',
        'f3de93555ceb01c4a3549c9246e26e80',
        '0cbe961fa7e90673b4f0fd044e34f482',
        'cb161a9fb97bbf587537aaa2f3ae509c',
        '755c57f708bdd8fb328be94e42208896',
        '2995c0f9bf938b0bef995963259ed0c1',
        '905a4e2847c7e2c9d6d7e288616d36c4',
        'ae7a1f4106ac503f9c5b093c052cc650',
        '51273f24f060f3da9a41a37b0ee5189d',
        '90f367867c56e60c030f4328b080d38c',
        'd69ac2f73f24f4677b80bcdc352c67c3',
        '344e78663dc05056da366dc30bb7a272',
    ]

    for idx, department in enumerate(m.Department.objects):
        dep = department.id
        try:
            file_path = os.path.join(
                sys.path[0], '%s/%s.txt' % (c.UWDATA_COURSES_DATA_DIR, dep))

            if file_exists(file_path):
                continue

            api_key = api_keys[idx % len(api_keys)]
            url = 'http://api.uwdata.ca/v1/faculty/%s/courses.json?key=%s' % (dep, api_key)
            data = get_data_from_url(url, num_tries=1)
            courses = data['courses']

            with open(file_path, 'w') as f:
                f.write(json.dumps(courses))
            print 'good dep: %s' % dep

        except Exception as ex:
            print 'exp: %s' % ex
            print 'bad dep: %s' % dep

        time.sleep(3)


def get_opendata_courses():
    courses = {}
    file_names = glob.glob(os.path.join(sys.path[0],
                                        '%s/*.txt' % c.REVIEWS_DATA_DIR))
    for file_name in file_names:
        f = open(file_name, 'r')
        data = json.load(f)
        f.close()
        for rating in data['ratings']:
            course = rating['class']
            if course is None:
                continue
            course = course.strip().lower()
            matches = re.findall(r'([a-z]+).*?([0-9]{3}[a-z]?)(?:[^0-9]|$)',
                                 course)
            if len(matches) != 1 or len(matches[0]) != 2:
                continue
            dep = matches[0][0]
            if not m.Department.objects.with_id(dep):
                continue
            if not dep in courses:
                courses[dep] = set()
            print 'Matched regex {dep}{num}'.format(dep=dep, num=matches[0][1])
            courses[dep].add(matches[0][1])

    errors = []
    api_key = s.OPEN_DATA_API_KEY
    bad_courses = 0
    bad_course_names = set()
    good_courses = 0
    # TODO(mack): this is only crawling course info for courses which have
    # menlo rating info; should be crawling all courses
    for dep in courses:
        dep_courses = {}
        print 'Processing department {dep}'.format(dep=dep)
        for num in courses[dep]:
            if num in dep_courses:
                continue
            print '  Processing number {num}'.format(num=num)
            query = dep + num
            url = ('http://api.uwaterloo.ca/public/v1/' + \
                    '?key={api_key}&service=CourseInfo&q={query}&output=json'
                    .format(api_key=api_key, query=query))
            data = get_data_from_url(url)
            try:
                data = data['response']['data']
            except:
                is_bad_course = True

            if not data:
                is_bad_course = True
            elif isinstance(data['result'], list):
                is_bad_course = True
                print ('More than one result for query {query}'
                        .format(query=query))

            if is_bad_course:
                bad_courses += 1
                bad_course_names.add(query)
                error = 'Found new bad course {course}'.format(course=query)
                print error
                errors.append(error)
            else:
                good_courses += 1
                dep_courses[num] = data['result']
                print 'Found new course {query}'.format(query=query)
        try:
            f = open(os.path.join(
                        sys.path[0],
                        '%s/%s.txt' % (c.OPENDATA_COURSES_DATA_DIR, dep)), 'w')
            f.write(json.dumps(dep_courses))
            f.close()
        except Exception:
            errors = 'Exception writing to file {dep}.txt'.format(dep=dep)
            errors.append(error)
            print error
            traceback.print_exc(file=sys.stdout)

    print 'Found {num} errors'.format(num=len(errors))
    count = 0
    for error in errors:
        count += 1
        print count, ':', error

    print 'Found {num} bad courses'.format(num=bad_courses)
    print 'Found {num} good courses'.format(num=good_courses)
    print 'Bad course names: {names}'.format(names=bad_course_names)


def get_opendata_exam_schedule():
    api_key = s.OPEN_DATA_API_KEY
    current_term_id = m.Term.get_current_term_id()
    current_quest_termid = m.Term.get_quest_id_from_term_id(current_term_id)
    url = ('http://api.uwaterloo.ca/v2/terms/{term_id}/examschedule.json'
           '?key={api_key}').format(api_key=api_key,
                                    term_id=current_quest_termid)

    data = get_data_from_url(url)
    try:
        data = data['data']
    except KeyError:
        print "crawler.py: ExamSchedule API call failed with data:\n%s" % data
        raise

    today = datetime.datetime.today()
    file_name = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '%s/uw_exams_%s.txt' % (c.EXAMS_DATA_DIR, today.strftime('%Y_%m_%d')))
    with open(file_name, 'w') as f:
        json.dump(data, f)


# TODO(david): This needs to be updated on a regular basis and not use
#     uwlive.ca (hopefully get data from OpenData)
def get_terms_offered():
    found = 0
    missing_course_ids = []

    terms_offered_by_course = {}
    css_class_to_term = {
        'offer-spring': 'S',
        'offer-winter': 'W',
        'offer-fall': 'F',
    }

    def save_data():
        print 'writing to file'

        file_name = os.path.join(
                sys.path[0], '%s/terms_offered.txt' % c.TERMS_OFFERED_DATA_DIR)
        with open(file_name, 'w') as f:
            json.dump(terms_offered_by_course, f)

        file_name = os.path.join(
                        sys.path[0],
                        '%s/missing_courses.txt' % c.TERMS_OFFERED_DATA_DIR)
        with open(file_name, 'w') as f:
            json.dump(missing_course_ids, f)

    for course in list(m.Course.objects):
        terms_offered_by_course[course.id] = []

        if len(terms_offered_by_course) % 100 == 0:
            save_data()

        department_id = course.department_id
        number = course.number

        url = 'http://uwlive.ca/courselect/courses/%s/%s' % (
                department_id, number)
        html_tree = html_parse(url, num_tries=1)
        if html_tree is None:
            missing_course_ids.append(course.id)
        else:
            for css_class, term_code in css_class_to_term.items():
                if html_tree.xpath('.//li[@class="%s"]' % css_class):
                    terms_offered_by_course[course.id].append(term_code)

        if len(terms_offered_by_course[course.id]):
            found += 1
            print '+ %s' % course.id
        else:
            print '- %s' % course.id

        time.sleep(0.5)

    save_data()

    print 'FOUND: %d' % found
    print 'MISSING: %d' % len(missing_course_ids)


def get_subject_sections_from_opendata(subject, term):
    """Get info on all sections offered for all courses of a given subject and
    term.

    Args:
        subject: The department ID (eg. CS)
        term: The 4-digit Quest term code (defaults to current term)
    """
    url = ('{api_url}/terms/{term}/{subject}/schedule.json'
            '?key={api_key}'.format(
                api_url=API_UWATERLOO_V2_URL,
                api_key=s.OPEN_DATA_API_KEY,
                subject=subject,
                term=term,
    ))

    data = get_data_from_url(url)
    try:
        sections = data['data']
    except (KeyError, TypeError):
        logging.exception("crawler.py: Schedule API call failed with"
                " url %s and data:\n%s" % (url, data))
        raise

    return sections


def get_opendata_sections():
    current_term_id = m.Term.get_current_term_id()
    next_term_id = m.Term.get_next_term_id()

    # TODO(david): Need to regularly update departments from OpenData:
    #     https://api.uwaterloo.ca/v2/codes/subjects.json
    # We resolve the query (list()) because Mongo's cursors can time out
    for department in list(m.Department.objects):
        sections = []
        for term_id in [current_term_id, next_term_id]:
            quest_term_id = m.Term.get_quest_id_from_term_id(term_id)
            sections += get_subject_sections_from_opendata(
                    department.id.upper(), quest_term_id)

        # Now write all that data to file
        filename = os.path.join(os.path.dirname(__file__),
                '%s/%s.json' % (c.SECTIONS_DATA_DIR, department.id))
        with open(filename, 'w') as f:
            json.dump(sections, f)


if __name__ == '__main__':
    me.connect(c.MONGO_DB_RMC)

    parser = argparse.ArgumentParser()
    supported_modes = ['departments', 'ucalendar_courses', 'opendata_courses',
            'uwdata_courses', 'terms_offered', 'opendata_sections']

    parser.add_argument('mode', help='one of %s' % ','.join(supported_modes))
    args = parser.parse_args()

    if args.mode == 'departments':
        get_departments()
    elif args.mode == 'ucalendar_courses':
        get_ucalendar_courses()
    elif args.mode == 'opendata_courses':
        get_opendata_courses()
    elif args.mode == 'uwdata_courses':
        get_uwdata_courses()
    elif args.mode == 'terms_offered':
        get_terms_offered()
    elif args.mode == 'opendata_exam_schedule':
        get_opendata_exam_schedule()
    elif args.mode == 'opendata_sections':
        get_opendata_sections()
    else:
        sys.exit('The mode %s is not supported' % args.mode)
