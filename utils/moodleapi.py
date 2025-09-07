import requests
import json

from django.conf import settings

moodle_api_url = settings.MOODLE_API_URL
moodle_api_token = settings.MOODLE_API_TOKEN

### Users ###
def create_user_in_moodle(email, first_name, last_name):

    params = {
        'wstoken': moodle_api_token,
        'wsfunction': 'core_user_create_users',
        'moodlewsrestformat': 'json',
        'users[0][username]': email,
        'users[0][firstname]': first_name,
        'users[0][lastname]': last_name,
        'users[0][email]': email,
        'users[0][auth]': 'db',
    }

    response = requests.post(moodle_api_url, params=params)
    return response.text
    # [{"id":8,"username":"test@testy.com"}]


def generate_moodle_token(username, password):
    moodle_token_url = "https://moodle.valerievv.com/login/token.php"
    params = {
        "username": username,
        "password": password,
        "service": "django",
    }

    response = requests.get(moodle_token_url, params=params)
    token = response.json().get("token")

    return token

### Courses ###
def user_enrolled_courses(moodle_id):

    params = {
        'wstoken': moodle_api_token,
        'wsfunction': 'core_enrol_get_users_courses',
        'moodlewsrestformat': 'json',
        'userid': moodle_id,
    }

    response = requests.post(moodle_api_url, params=params)
    enrolled_courses = json.loads(response)
    return enrolled_courses


def get_course_contents(course_id):

    params = {
        'wstoken': moodle_api_token,
        'wsfunction': 'core_course_get_contents',
        'moodlewsrestformat': 'json',
        'courseid': course_id,
    }

    response = requests.post(moodle_api_url, params=params)

    course_contents = response.json()
    return course_contents


def get_all_courses():

    params = {
        'wstoken': moodle_api_token,
        'wsfunction': 'core_course_get_courses',
        'moodlewsrestformat': 'json',
    }

    response = requests.post(moodle_api_url, params=params)

    course_contents = response.json()
    return course_contents

def get_course_categories():

    params = {
        'wstoken': moodle_api_token,
        'wsfunction': 'core_course_get_categories',
        'moodlewsrestformat': 'json',
    }

    response = requests.post(moodle_api_url, params=params)

    course_contents = response.json()
    return course_contents


