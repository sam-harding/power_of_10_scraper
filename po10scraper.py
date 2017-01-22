from bs4 import BeautifulSoup
import urllib
import pprint
import re
#import redis as redis_module
import mysql.connector as mariadb
import sys

#set up pretty printer
pp = pprint.PrettyPrinter(indent = 4)
event_list_milliseconds = ["60", "100", "150", "200", "400", "600", "800", "1500", "3000", "5000", "10000", "3000SC", "5K", "parkrun"]
event_list_millimetres = ["LJ", "SP5K"]
event_list_ignore = ["ZXC"]
convert_blocker = ["DNF", "DNS", "DQ", "TBC"]

#Initialize MariaDB Connection
mariadb_connection = mariadb.connect(user='root', password='', database='power_of_ten')
cursor = mariadb_connection.cursor()


def cycle_through_ranking_table(event = "100", age_group = "ALL", sex = "M", year = "2016", debug = False):
  # Initialize output variables
  output = []
  output_headers = []

  #Resolve parameters into ranking url
  #eg. http://www.powerof10.info/rankings/rankinglist.aspx?event=800&agegroup=ALL&sex=M&year=2016
  if debug == True:
    url = "file:///Users/sam/Development/power_of_10/webpages/800mranking.html"
  else:
    url = "http://www.powerof10.info/rankings/rankinglist.aspx?event=" + event + "&agegroup=" + age_group + "&sex=" + sex + "&year=" + year

  # Initialize URL and BeautifulSoup
  r = urllib.urlopen(url).read()
  soup = BeautifulSoup(r, "html.parser")

  # Iterate through rankings
  table = soup.find("span", {"id" : "cphBody_lblCachedRankingList"}).find("table").find_all("tr")
  output_hash = {}
  for row in table:

    if "style" in row.attrs:
      print(row.prettify())
      continue
    elif row.get('class')[0] == 'rankinglistsubheader':
      if row.text == "Resident Non UK Athletes":
        break
    else:
      count = 0
      skip = False
      another_time = 0
      for item in row:
        # Handle ranking place
        if count == 0:
          if item.text == '':
            another_time += 1
          elif not item.text.isdigit():
            skip = True
          else:
            output_hash = {}
            output_hash["rank"] = item.text

          if skip:
            continue



        if count == 1:
          if not another_time:
            output_hash["perf"] = time_to_milliseconds(item.text)
          elif another_time > 0:
            output_hash["other_perf_" + str(another_time)] = item.text.lstrip()

        if count == 2:
          if item.text != '':
            if another_time > 0:
              output_hash["other_perf_" + str(another_time) + "_flag"] = item.text
            else:
              output_hash["perf_flag"] = item.text

        if count == 3:
          if another_time == 0:
            output_hash["perf_wind"] = item.text
          elif another_time > 0:
            output_hash["other_perf_" + str(another_time) + "_wind"] = item.text

        if count == 4:
          if another_time == 0:
            output_hash["pb"] = time_to_milliseconds(item.text)

        if count == 5:
          if another_time == 0:
            if item.text == "PB":
              output_hash["is_pb"] = True
            else:
              output_hash["is_pb"] = False

        if count == 6:
          if another_time == 0:
            output_hash["name"] = item.text
            url_to_get = item.a["href"]
            #Regex to get id from http://www.thepowerof10.info/athletes/profile.aspx?athleteid=2326
            #Regex to get id from
            m = re.search('(?<=athleteid=)\d+', url_to_get)
            output_hash["athlete_id"] = m.group(0)

        if count == 7:
          if another_time == 0:
            output_hash["age_flag"] = item.text

        if count == 8:
          if another_time == 0:
            output_hash["DoB"] = item.text

        if count == 9:
          if another_time == 0:
            output_hash["lead_coach"] = item.text

        if count == 10:
          if another_time == 0:
            output_hash["club"] = item.text

        if count == 11:
          if another_time == 0:
            output_hash["perf_venue"] = item.text
          elif another_time > 0:
            output_hash["other_perf_" + str(another_time) + "_venue"] = item.text

        if count == 12:
          if another_time == 0:
            output_hash["perf_date"] = item.text
          elif another_time > 0:
            output_hash["other_perf_" + str(another_time) + "_date"] = item.text



        count += 1

    if not another_time or skip:    
      output.append(output_hash)

  print len(output)
  return output



def convert_ranking_table_2_hash(debug = False, event = "100", age_group = "ALL", sex = "M", year = "2016"):
  #Initialize output variables
  output = []
  output_headers = []
  
  #Resolve parameters into ranking url
  #eg. http://www.powerof10.info/rankings/rankinglist.aspx?event=800&agegroup=ALL&sex=M&year=2016
  if debug == True:
    url = "file:///Users/sam/Development/power_of_10/webpages/800mranking.html"
  else:
    url = "http://www.powerof10.info/rankings/rankinglist.aspx?event=" + event + "&agegroup=" + age_group + "&sex=" + sex + "&year=" + year


  #Initialize URL and BeautifulSoup
  r = urllib.urlopen(url).read()
  soup = BeautifulSoup(r, "html.parser")

  #Find headers and distribute to varible so can reference later on
  headers = soup.find_all("tr", class_="rankinglistheadings")

  for header_title in headers:
    row = header_title.find_all("td")

    for item in row:
      output_headers.append(item.get_text())

  #Iterate through rankings
  table_row = soup.find_all("tr", class_="rlr")
  table_row += soup.find_all("tr", class_="rlra")
  for index, element in enumerate(table_row):
    output_hash = {}
    
    #Iterate through row of rankings and sort each column
    row = element.find_all("td")
    for idx, i in enumerate(row):
      #If has a link and column header isnt blank. Regex for id
      if i.a != None and output_headers[idx] != "":
        url_to_get = i.a["href"]
        #Regex to get id from http://www.thepowerof10.info/athletes/profile.aspx?athleteid=2326
        #Regex to get id from
        m = re.search('(?<=athleteid=)\d+|(?<=meetingid=)\d+', url_to_get)
        if m != None:
          re_id = m.group(0)
        else:
          re_id = None

        output_hash[output_headers[idx] + "_id"] = re_id
      output_hash[output_headers[idx]] = i.get_text()

    if output_hash["Name"] == "":
      continue #continue if Name is none because it is a wind time
    output.append(output_hash)
    #print(output_hash)
    #Insert athlete into ranking on redis
    #redis.incr("ranking_count")
    #ranking_count = redis.get("ranking_count")

    # Make sure perf and pb are converted
    if event in event_list_milliseconds:
      perf = time_to_milliseconds(output_hash["Perf"])
      pb = time_to_milliseconds(output_hash["PB"])
    elif event in event_list_millimetres:
      perf = distance_to_millimetres(output_hash["Perf"])
      pb = distance_to_millimetres(output_hash["PB"])
    elif event in event_list_ignore:
      continue
    else:
      print(event + " not found. Perf = " + perf)

    #redis.sadd("ranking_" + event + "_" + age_group + "_" + sex + "_" + year, ranking_count)
    #redis.hmset("ranking_id:" + str(ranking_count), 
                # {"athlete_id": output_hash["Name_id"],
                # "athlete_name": output_hash["Name"],
                # "perf": perf,
                # "pb": pb})
  return output


def convert_athlete_2_hash(debug = False, athlete_id = None):
  #Initialize output variables
  output = {}
  output["perf"] = []
  output_headers = []
  athlete_pbs = {}

  #Resolve parameters into ranking url
  #eg. http://www.powerof10.info/athletes/profile.aspx?athleteid=1382
  if debug == True:
    url = "file:///Users/sam/Development/power_of_10/webpages/samharding.html"
  else:
    url = "http://www.powerof10.info/athletes/profile.aspx?athleteid=" + athlete_id
  #Initialize URL and Beautiful Soup
  r = urllib.urlopen(url).read()
  soup = BeautifulSoup(r, "html.parser")
  

  #Get athlete name
  ath_name = soup.find_all("tr", class_="athleteprofilesubheader")
  ath_name = ath_name[0].find_all("td")
  ath_name = ath_name[0].find_all("h2")
  ath_name[0].get_text().lstrip()
  #redis.hset(athlete_id, "name_full", ath_name[0].get_text().lstrip())

  #Get athlete information
  ath_info = soup.find_all("div", id="cphBody_pnlAthleteDetails")
  ath_info = ath_info[0].find_all("table", cellpadding="2")
  for element_i in ath_info:
    ath_info_block = element_i.find_all("tr")
    for element_j in ath_info_block:
      split = element_j.get_text().split(":", 1)
      output[split[0]] = split[1]

  #Find headers and distribute to varible so can reference later on
  headers = soup.find_all("tr", style="background-color:LightGrey;")
  for header_title in headers:
    row = header_title.find_all("td")

    for item in row:
      output_headers.append(item.get_text())

  #Iterate through results
  results = soup.find_all("div", id="cphBody_pnlPerformances")
  table_row = results[0].find_all("tr", style="background-color:WhiteSmoke;")
  table_row += results[0].find_all("tr", style="background-color:Gainsboro;")
  for element in table_row:
    output_hash = {}

    #iterate through results and sort by column
    row = element.find_all("td")
    for idx, i in enumerate(row):
      #If has a lunk and column header isnt blank. Regex for id
      if i.a != None and output_headers[idx] != "":
        url_to_get = i.a["href"]
        output_hash[output_headers[idx] +  "_id"] = url_to_get
        #print("Searching " + url_to_get)
        m = re.search("(?<==).+?&", url_to_get)
        #print(m.group(0))



      output_hash[output_headers[idx]] = i.get_text()
      if output_headers[idx] == "Event":
        event = i.get_text()
      elif output_headers[idx] == "Perf":
        perf = i.get_text()

    if perf not in convert_blocker:
      if event in event_list_milliseconds:
        perf = time_to_milliseconds(perf)
      elif event in event_list_millimetres:
        perf = distance_to_millimetres(perf)
      elif event in event_list_ignore:
        continue
      else:
        print(event + " not found. Perf = " + perf)
      if event not in athlete_pbs or perf < athlete_pbs[event]:
        athlete_pbs[event] = perf

    output["perf"].append(output_hash)

  # Put PBs to Redis
  #for pb_event, pb_result in athlete_pbs.items():
    #redis.hset(athlete_id, "pb:" + pb_event, pb_result)
  return output


def is_time_automatic(time_string):
  if (re.search('[a-zA-Z]', time_string)):
    time_string = re.sub("[a-zA-Z]", "", time_string)
  else:
    time_string = time_string

  split_time = time_string.split(".")
  if len(split_time) != 2:
    print("is_time_automatic fails on " + time_string)
    return False
  if len(split_time[1]) == 1:
    return False
  else:
    return True

def time_to_milliseconds(time_string):
  #strip i from string if indoor
  if (re.search('[a-zA-Z]', time_string)):
    time_string = re.sub("[a-zA-Z]", "", time_string)
  else:
    time_string = time_string


  output_time = 0
  seconds = time_string
  #Split time in to its minutes
  split_time = time_string.split(":")
  if len(split_time) == 2:
    output_time += 60000 * int(split_time[0])
    seconds = split_time[1]
  if len(split_time) < 1 or len(split_time) > 2:
    print("time_to_milliseconds has gone mad with " + time_string)

  #Split seconds into its second and millisecond part
  seconds_split = seconds.split(".")
  output_time += 1000 * int(seconds_split[0])
  if len(seconds_split) == 2:
    if len(seconds_split[1]) == 2:
      output_time += 10 * int(seconds_split[1])
    elif len(seconds_split[1]) == 3:
      output_time += int(seconds_split[1])
    elif len(seconds_split[1]) == 1:
      output_time += 100 * int(seconds_split[1])
    else:
      print("Something has gone wrong trying to split " + seconds_split)

  return output_time

def distance_to_millimetres(distance_string):
  output_distance = 0
  metres = distance_string
  #Split distance into its metres
  split_distance = distance_string.split(".")
  if len(split_distance) == 2:
    output_distance += 1000 * int(split_distance[0])
    output_distance += 10 * int(split_distance[1])
  else:
    print("distance_to_millimetres has gone mad with " + distance_string)

  return output_distance


#pp.pprint(convert_ranking_table_2_hash(debug = True))
#pp.pprint(convert_ranking_table_2_hash(event = "100", age_group = "ALL", sex = "M"))
#pp.pprint(cycle_through_ranking_table(event = "100", age_group = "ALL", sex = "M"))

#print(time_to_milliseconds("53.630"))


#convert_athlete_2_hash(athlete_id = "208016")
#pp.pprint(convert_athlete_2_hash('file:///Users/sam/Development/power_of_10/webpages/samharding.html'))
#convert_athlete_2_hash('file:///Users/sam/Development/power_of_10/webpages/samharding.html')

def iterate_through_and_load():
  ranking_array = convert_ranking_table_2_hash(event = "100", age_group = "ALL", sex = "M")
  count = 0
  for each in ranking_array:
    try:
      convert_athlete_2_hash(athlete_id = each["Name_id"])
    except KeyError:
      print(each)
    print("Loaded " + each["Name"] + " count = " + str(count))
    count += 1
    if count > 60:
      break


#iterate_through_and_load()



def iterate_rankings_and_load():
  events = ["100"] #, "200", "400", "800", "1500", "3000", "5000", "10000", "3000SC"]
  years = ["2016"]#, "2015", "2014", "2013", "2012", "2011", "2010", "2009", "2008", "2007", "2006", "alltime"]
  genders = ["M", "W"]
  age_groups = ["ALL"]
  ranking_id_count = 0

  for event in events:
    for year in years:
      for gender in genders:
        for age_group in age_groups:
          #convert_ranking_table_2_hash(event = event, age_group = age_group, sex = gender, year = year)
          print ("Loading " + event + " " + age_group + " " + gender + " " + year)
          ranking_hash = cycle_through_ranking_table(event = event, age_group = age_group, year = year, sex = gender)
          #redis.flushdb()
          cursor.execute("DELETE FROM ranking WHERE ranking_year = %s AND ranking_gender = %s AND ranking_event = %s AND ranking_age = %s", (year, gender, event, age_group))

          for r in ranking_hash:
            print r
            if "perf" in r:
              cursor.execute("INSERT INTO ranking (rank, perf, is_main, pb, name, age_group, ranking_year, ranking_event, ranking_gender, ranking_age, athlete_id) \
                                          VALUES (%s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s)", 
                                          (r["rank"], r["perf"], r["pb"], r["name"], r["age_flag"], year, event, gender, age_group, r["athlete_id"]))
              pass
              #print("Ranking perf = " + ranking["perf"])
              #ranking_id = "ranking_id:" + str(ranking_id_count)
              #perf = time_to_milliseconds(ranking["perf"])
              #redis.zadd("ranking:" + event + ":" + age_group + ":" + gender + ":" + year, perf, ranking_id)
            mariadb_connection.commit()
iterate_rankings_and_load()