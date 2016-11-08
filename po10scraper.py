from bs4 import BeautifulSoup
import urllib
import pprint
import re
import redis
import sys

#set up pretty printer
pp = pprint.PrettyPrinter(indent = 4)
event_list_milliseconds = ["60", "100", "150", "200", "400", "600", "800", "1500", "3000", "5000", "10000", "5K", "parkrun"]
event_list_millimetres = ["LJ", "SP5K"]
event_list_ignore = ["ZXC"]
convert_blocker = ["DNF", "DNS", "DQ", "TBC"]

#Initialize Redis Connection
redis = redis.StrictRedis(host='localhost', port=6379)
redis.flushdb()

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

    output.append(output_hash)
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
  redis.hset(athlete_id, "name_full", ath_name[0].get_text().lstrip())

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
  for pb_event, pb_result in athlete_pbs.items():
    redis.hset(athlete_id, "pb:" + pb_event, pb_result)
  return output

def time_to_milliseconds(time_string):
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


iterate_through_and_load()



