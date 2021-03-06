import os
import gc
import psycopg2
import urlparse
import tinys3

s3conn = tinys3.Connection(os.environ['AWS_ACCESS_KEY'],os.environ['AWS_SECRET_KEY'],tls=True)
bucket = os.environ['S3_BUCKET']

from json import dumps, load
from mailin import Mailin
from uwaterlooapi import UWaterlooAPI
# from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()

# dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
# load_dotenv(dotenv_path)

uw = UWaterlooAPI(api_key=os.environ['UW_API_TOKEN'])
m = Mailin("https://api.sendinblue.com/v2.0", os.environ['SENDINBLUE_API_KEY'])

# Connect to database
urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])

conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

subjects = uw.subject_codes()
allTermInfo = uw.terms()
terms = allTermInfo['listings']

###### NOTE: ALL PATHS ARE FROM THE TOP LEVEL DIRECTORY AS THESE RUN ON HEROKU ########

# Cronjob for current term courses
# @sched.scheduled_job('interval', minutes=290)
# def generateCoursesForCurrentTerm():
# 	print "Generating courses for current term"
# 	terms = [str(allTermInfo['current_term'])]
# 	for term in terms:
# 		courseMatches = []
# 		for subject in subjects:
# 			courses = uw.term_subject_schedule(term, subject['subject'])
# 			for course in courses:
# 				courseMatches.append(course)
# 		# Write to the file
# 		try:
# 			jsonFile = open('data/courses.json', 'r');
# 			data = load(jsonFile);
# 			jsonFile.close();

# 			data[term] = courseMatches;

# 			jsonFile = open('data/courses.json', 'w+');
# 			jsonFile.write(dumps(data));
# 			jsonFile.truncate();
# 			jsonFile.close();
# 		except Exception as e:
# 			print e

# 	# f = open(term + '.json', 'rb')
# 	# s3conn.upload(term + '.json',f,bucket)
# 	# s3conn.update_metadata(term + '.json',bucket=bucket,public=True)
# 	print "Finished generating courses for current term"
# 	gc.collect()

# Cronjob for current term courses
# @sched.scheduled_job('interval', minutes=300)
# def generateCoursesForNextTerm():
# 	print "Generating courses for next term"
# 	terms = [str(allTermInfo['next_term'])]
# 	for term in terms:
# 		courseMatches = []
# 		for subject in subjects:
# 			courses = uw.term_subject_schedule(term, subject['subject'])
# 			for course in courses:
# 				courseMatches.append(course)
# 		# Write to the file
# 		try:
# 			jsonFile = open('data/courses.json', 'r');
# 			data = load(jsonFile);
# 			jsonFile.close();

# 			data[term] = courseMatches;

# 			jsonFile = open('data/courses.json', 'w+');
# 			jsonFile.write(dumps(data));
# 			jsonFile.truncate();
# 			jsonFile.close();
# 		except Exception as e:
# 			print e

# 	# f = open(term + '.json', 'rb')
# 	# s3conn.upload(term + '.json',f,bucket)
# 	# s3conn.update_metadata(term + '.json',bucket=bucket,public=True)
# 	print "Finished generating courses for next term"

# Cronjob for all terms courses
# @sched.scheduled_job('cron', day_of_week='sun', hour=17)
# def generateCoursesForAllTerms():
# 	print "Generating courses for all terms"
# 	for year in terms:
# 		for term in terms[year]:
# 			term = str(term['id'])
# 			courseMatches = []
# 			for subject in subjects:
# 				courses = uw.term_subject_schedule(term, subject['subject'])
# 				for course in courses:
# 					courseMatches.append(course)
# 			# Write to the file
# 			try:
# 				jsonFile = open('data/courses.json', 'r');
# 				data = load(jsonFile);
# 				jsonFile.close();

# 				data[term] = courseMatches;

# 				jsonFile = open('data/courses.json', 'w+');
# 				jsonFile.write(dumps(data));
# 				jsonFile.truncate();
# 				jsonFile.close();
# 			except Exception as e:
# 				print e

# 			# f = open(term + '.json', 'rb')
# 			# s3conn.upload(term + '.json',fr,bucket)
# 			# s3conn.update_metadata(term + '.json',bucket=bucket,public=True)
# 	print "Finished generating courses for all terms"

@sched.scheduled_job('cron', day_of_week='sun', hour=18)
def generateSubjects():
	print "Generating subjects"
	subjects = uw.subject_codes()
	f = open('data/subjects.json', 'r+')
	f.write(dumps(subjects))
	f.truncate()
	f.close()

	# f = open('subjects.json', 'rb')
	# s3conn.upload('subjects.json',f,bucket)
	# s3conn.update_metadata('subjects.json',bucket=bucket,public=True)
	print "Finished generating subjects"

@sched.scheduled_job('cron', day_of_week='sun', hour=19)
def generateTerms():
	print "Generating terms"
	terms = uw.terms()
	f = open('data/terms.json', 'r+')
	f.write(dumps(terms))
	f.truncate()
	f.close()

	# f = open('terms.json', 'rb')
	# s3conn.upload('terms.json',f,bucket)
	# s3conn.update_metadata('terms.json',bucket=bucket,public=True)
	print "Finished generating terms"

@sched.scheduled_job('interval', minutes=15)
def generateEmails():
	print "Generating emails"
	cur = conn.cursor()
	try:
	    cur.execute("""SELECT * from Subscriptions""")
	except:
	    print "Cursor can't SELECT from Subscriptions"

	# Is course number unique for course & term or not?
	rows = cur.fetchall()
	for row in rows:
		# Id, Course, Email
		# 0 , 1     , 2
		course = uw.schedule_by_class_number(row[1])
		course = course[0] if course else None
		if course and course['enrollment_total'] < course['enrollment_capacity']:
			print "Course now open!"
			#Send email
			try:
				message = {
					"from" : ['info@uwcourses.com' ,"UW Courses"],
					'html': '<p>Hey!</p><p>You know that course you subscribed to: ' + str(row[2]) + '?</p><p>It has opened up!</p><p>Best of luck getting it!</p>',
					'headers': {'website': 'www.uwcourses.com'},
					'text': 'Hey! You know that course you subscribed to with course number ' + str(row[2]) + '? It has opened up! Best of luck getting it!',
					"to" : { row[3] : row[3] },
					'subject': str(row[1]) + ' Course Opening'
				}

				result = m.send_email(message)
				print(result)

			except Exception as e:
			    # Mandrill errors are thrown as exceptions
			    print 'An error occurred: %s - %s' % (e.__class__, e)

			#Remove from list
			try:
				cur.execute("DELETE FROM Subscriptions WHERE ClassNumber = %s AND Email = %s", (row[1], row[3]))
				print "Deleted the item from Subscriptions"
			except Exception as e:
				print e

	# Commit changes to DB
	conn.commit()
	print "Finished generating emails"

# generateSubjects()
# generateTerms()
# generateCoursesForCurrentTerm()
# generateCoursesForNextTerm()
# generateCoursesForAllTerms()
sched.start()