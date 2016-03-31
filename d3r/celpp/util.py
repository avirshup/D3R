# -*- coding: utf-8 -*-

import os
import logging
import re
import urllib
import time
import gzip
from datetime import date
from datetime import timedelta

logger = logging.getLogger(__name__)

DAYS_IN_WEEK = 7

DATA_SET_WEEK_PREFIX = 'dataset.week.'


class DownloadError(Exception):
    """Exception to denote error downloading data
    """
    pass


def get_all_celpp_years(celppdir):
    """Given a directory find all year directories within

       This method looks for all directories within `celppdir`
       that fit the structure of a year directory ####
       or the regex ^\d\d\d\d$.
       Full paths to those directories are returned
       :return: List year directories, note path is NOT prefixed
       :raises: Exception if celppdir is not a directory
    """
    if not os.path.isdir(celppdir):
        raise Exception(celppdir + " is not a directory")

    year_list = []
    dir_pattern = re.compile("^\d\d\d\d$")
    for entry in os.listdir(celppdir):
        if re.match(dir_pattern, entry):
            full_path = os.path.join(celppdir, entry)
            if os.path.isdir(full_path):
                year_list.append(entry)

    return year_list


def find_latest_year(celppdir):
    """Given a directory find the latest year

       The latest year will be a folder of 4 digits
       and have the highest value ie 2015
       :return: Directory or None if none is found
       :raises: Exception: If celppdir is not a directory
       """

    if not os.path.isdir(celppdir):
        raise Exception(celppdir + " is not a directory")

    latest_year = -1
    latest_entry = None
    full_path = None
    for entry in get_all_celpp_years(celppdir):
            entry_year = int(entry)
            if entry_year > latest_year:
                full_path = os.path.join(celppdir, entry)
                if os.path.isdir(full_path):
                    latest_year = entry_year
                    latest_entry = full_path

    if latest_year == -1:
        return

    return latest_entry


def get_celpp_year_from_path(dir):
    """Given path extract the year number from it

       Expects path of
       /..../year/dataset.week.#
       or year/dataset.week.#

    :param dir: full or partial path to week
    :return year #### from path or '0' if year extracted is not a 4
    digit number
    """
    if dir is None:
        raise Exception('Path is none')

    remove_week = re.sub("\/" + DATA_SET_WEEK_PREFIX + ".*$", "", dir)
    year = re.sub("^.*\/", "", remove_week)

    dir_pattern = re.compile("^\d\d\d\d$")

    if not re.match(dir_pattern, year):
        logger.warning('Year ( ' + year + ' ) extracted from ' + dir +
                       ' is not a 4 digit number')
        return '0'
    return year


def get_all_celpp_weeks(celpp_year_dir):
    """Given a celpp year directory get all week directories

       Expects celpp_year_dir to be full path to year dir ie ####/
       and finds all directories of format dataset.week.#
       returning a list of the week numbers ie #
       :returns: List of week numbers
       :raises Exception: If celpp_year_dir is not a directory
    """
    if not os.path.isdir(celpp_year_dir):
        raise Exception(celpp_year_dir + " is not a directory")

    week_list = []

    dir_pattern = re.compile("^" + DATA_SET_WEEK_PREFIX + "\d+$")

    for entry in os.listdir(celpp_year_dir):
        if re.match(dir_pattern, entry):
            weeknum = re.sub(DATA_SET_WEEK_PREFIX, "", entry)
            full_path = os.path.join(celpp_year_dir, entry)
            if os.path.isdir(full_path):
                week_list.append(weeknum)

    return week_list


def find_latest_weekly_dataset(celppdir):
    """Given a directory find the latest dataset

       This method looks in directory passed in for
       paths with dataset.week.# format and returns
       the path with highest # on it.  If none are
       found then None is returned.
       :return: Directory upon success or None if no directory found
       :raises: Exception: If celppdir is not a directory
       """
    latest_year = find_latest_year(celppdir)

    if latest_year is None:
        return

    latest_entry = None
    latest_weeknum = -1
    full_path = None
    for entry in get_all_celpp_weeks(latest_year):
            weeknum = int(entry)
            if weeknum > latest_weeknum:
                full_path = os.path.join(latest_year,
                                         DATA_SET_WEEK_PREFIX + entry)
                if os.path.isdir(full_path):
                    latest_weeknum = weeknum
                    latest_entry = full_path

    return latest_entry


def get_celpp_week_number_from_path(dir):
    """Given path extract the week number from it

       Expects either path of
       /..../year/dataset.week.#
       or dataset.week.#

    :param dir: full or partial path to week
    :return the # from dataset.week.# in `dir` path or '0' if value is
    not a 1-2 digit number
    """
    if dir is None:
        raise Exception('Path is none')

    weeknum = re.sub("^.*" + DATA_SET_WEEK_PREFIX, "", dir)

    dir_pattern = re.compile("^\d\d?$")
    if not re.match(dir_pattern, weeknum):
        logger.warning('Week number ( ' + weeknum + ' ) extracted from path '
                       + dir + ' is not a 2 digit number')
        return '0'
    return weeknum


def get_celpp_week_of_year_from_date(the_date):
    """ Returns CELPP week of year
        The CELPP week of year matches ISO week of year, but it
        starts on Friday instead of Monday.  The way it works is
        the code examines `the_date` and if its 12:00am Monday -
        11:59pm Thursday the current week according to date.isocalendar()
        is used.  If date falls between Friday 12:00am to Sunday 11:59pm
        this function advances the date to the following Monday and extracts
        week of year.
        :return: tuple with first value the week and second value the year
        :raises: Exception if `the_date` is None
    """
    if the_date is None:
        raise Exception('Must pass a valid date')
    assert isinstance(the_date, date)
    updated_date = the_date

    day_of_week = the_date.weekday()
    if day_of_week >= 4:
        updated_date = the_date + timedelta(days=(DAYS_IN_WEEK - day_of_week))
        logger.debug('Date ' + str(the_date) + ' is between Friday and ' +
                     'Sunday shifting date to ' + str(updated_date))

    return (updated_date.isocalendar()[1],
            updated_date.isocalendar()[0])


def create_celpp_week_dir(celpp_week_tuple, celppdir):
    """Creates celpp week dir in `celppdir`
    Creates celpp week directory under `celppdir`
    using `celpp_week_tuple` to get year and week of year
    diretories created:
    celppdir/<celpp_week_tuple[1]>/dataset.week.<celpp_week_tuple[0]>
    If directory already exists no operation is performed.
    :raises: OSError if unable to create directory
    """
    if celpp_week_tuple is None:
        raise Exception('celpp week tuple must be set')

    if celppdir is None:
        raise Exception('celppdir must be set')

    dir_to_create = os.path.join(celppdir, str(celpp_week_tuple[1]),
                                 'dataset.week.'+str(celpp_week_tuple[0]))
    if os.path.isdir(dir_to_create):
        logger.debug(dir_to_create +
                     ' directory already exists skipping creation')
        return

    logger.debug('Creating ' + dir_to_create)
    os.makedirs(dir_to_create, mode=0o775)


def download_url_to_file(url, download_path, num_retries,
                         retry_sleep_time_secs):
    """Downloads `url` to path specified by `download_path`

    Downloads `url` with built in retry `num_retries` and sleep
    `retry_sleep_time_secs` between retries
    :param url: url to download file from
    :param download_path: full path to file to write output to
    :param num_retries: number of retries, 0 means none, 1 means one retry
    :param retry_sleep_time_secs: # seconds delay between retry, cannot
                                  be negative
    :raises: DownloadError if there was an error downloading the file or
             one of the parameters has invalid value
    """

    if url is None:
        raise DownloadError('url is not set')

    if download_path is None:
        raise DownloadError('download_path is not set')

    if num_retries is None:
        num_retries = 0

    if retry_sleep_time_secs is None:
        retry_sleep_time_secs = 0

    if retry_sleep_time_secs < 0:
        raise DownloadError('retry sleep time cannot be negative')

    count = 0
    while count <= num_retries:
        logger.debug('Try # ' + str(count) + ' of ' +
                     str(num_retries) + ' to download ' +
                     download_path + ' from ' + url)
        try:
            (f, info) = urllib.urlretrieve(url, download_path)
            return
        except Exception:
            logger.exception('Caught exception trying to download file')
        count += 1
        logger.debug('Download failed, sleeping ' +
                     str(retry_sleep_time_secs) +
                     'seconds')
        time.sleep(retry_sleep_time_secs)

    raise DownloadError('Unable to download file from ' +
                        url + ' to ' + download_path)


def gunzip_file(gzip_file, dest_file):
    """Uses Python gzip library to uncompress gzip file

       :param gzip_file: path to file to gunzip
       :param dest_file: gunzip destination file
       :raises IOError: If there was a problem with operation
    """
    f_in = gzip.open(gzip_file, 'rb')
    f_out = open(dest_file, 'wb')
    for f in f_in:
        f_out.write(f)
    f_out.flush()
    f_out.close()
    f_in.close()


def append_string_to_file(dest_file, the_string):
    """Appends text in `the_string` to file set by `dest_file`

       Opens file specified by `dest_file` in append mode and
       writes `the_string` contents to the file.  Function then
       flushes and closes file.

       :param dest_file: File to append data to
       :param the_string: Data to append to file
       :raises IOError: If there is an issue writing data to the file
       :raises TypeError: If `dest_file` is None
    """
    f = open(dest_file, 'a')
    f.write(the_string)
    f.flush()
    f.close()


def get_file_line_count(the_file):
    """Counts number of lines in file

       Opens file and counts number of lines in
       file
       :param the_file: file to examine
       :raises TypeError: if `the_file` is None
       :raises IOError: if there is an issue reading the file
    """
    f = open(the_file, 'r')
    counter = 0
    for line in f:
        counter += 1
    f.close()
    return counter
