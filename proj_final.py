
from bs4 import BeautifulSoup
import requests
import json
import secret_api
import sqlite3
import csv
import plotly.plotly as py
import plotly.graph_objs as go


########## Set up at the beginning ##########

# Set up caching for google coordinate and US schools
CACHE_FNAME_schools = 'cache_schools.json'
try:
    cache_file_schools = open(CACHE_FNAME_schools, 'r')
    cache_contents_schools = cache_file_schools.read()
    CACHE_DICTION_schools = json.loads(cache_contents_schools)
    cache_file_schools.close()
except:
    CACHE_DICTION_schools = {}

CACHE_FNAME_GOOGLE = 'cache_GOOGLE.json'
try:
    cache_file_GOOGLE = open(CACHE_FNAME_GOOGLE, 'r')
    cache_contents_GOOGLE = cache_file_GOOGLE.read()
    CACHE_DICTION_GOOGLE = json.loads(cache_contents_GOOGLE)
    cache_file_GOOGLE.close()
except:
    CACHE_DICTION_GOOGLE = {}


# Set up a class for creating school instances
class School:
    def __init__(self, name, student_total, student_international, faculty_total, 
                 tuition, street, city, state, locale, longitude, latitude):
        self.name = name
        self.student_total = student_total
        self.student_international = student_international
        self.faculty_total = faculty_total
        self.tuition = tuition
        self.street = street
        self.city = city
        self.state = state
        self.locale = locale
        self.longitude = longitude
        self.latitude = latitude

# Set up a class for mapping
class Premap:
    def __init__(self, tup):
        self.name = tup[0]
        self.latitude = tup[-1]
        self.longitude = tup[-2]
 

########## Functions: Data Access and Storage ##########

# Get data from google caching and school caching
def get_unique_key(url):
    return url 

def params_unique_combination(baseurl, params_d, private_keys = ["key"]):
    alphabetized_keys = sorted(params_d.keys())
    res = []
    for k in alphabetized_keys:
        if k not in private_keys:
            res.append("{}-{}".format(k, params_d[k]))
    return baseurl + "_".join(res)


# Fetch school information from Web or the cache file
# input: an url
# return: a dictionary of web pages of US schools
def get_schools_using_cache(url):
    unique_ident = get_unique_key(url)

    if unique_ident in CACHE_DICTION_schools:
        return CACHE_DICTION_schools[unique_ident]
    
    else:
        page = requests.get(url).text
        CACHE_DICTION_schools[unique_ident] = page
        dumped_json_cache = json.dumps(CACHE_DICTION_schools)
        fw = open(CACHE_FNAME_schools,"w")
        fw.write(dumped_json_cache)
        fw.close()
        return CACHE_DICTION_schools[unique_ident]


# Fetch school GPS coordinates from either Google Place API or the cache file
# input: street, city, state of a school
# return: a dictionary of the GPS information about the school
def get_coordinate_using_cache(street, city, state): 

    query = street + ", " + city + ", " + state
    
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params_d = {}
    params_d["query"] = query 
    params_d["key"] = secret_api.google_places_key

    unique_ident = params_unique_combination(base_url, params_d)

    if unique_ident in CACHE_DICTION_GOOGLE:
        return CACHE_DICTION_GOOGLE[unique_ident]  

    else: 
        resp = requests.get(base_url, params_d)  
        resp_text = resp.text
        CACHE_DICTION_GOOGLE[unique_ident] = json.loads(resp_text) 
            
        dumps_data = json.dumps(CACHE_DICTION_GOOGLE) 
        cache_file = open(CACHE_FNAME_GOOGLE, "w") 
        cache_file.write(dumps_data)
        cache_file.close()
        return CACHE_DICTION_GOOGLE[unique_ident]


# Get the coordinate of the school from cache file
# input: street, city, state of a school
# return a dictionary of coordinates
def get_coordinate(street, city, state):
    loc = get_coordinate_using_cache(street, city, state)
    dict_loc = {}
    if len(loc["results"]) >= 1:
        dict_loc["latitude"] = loc["results"][0]["geometry"]["location"]["lat"]
        dict_loc["longitude"] = loc["results"][0]["geometry"]["location"]["lng"] 
    else:
        pass
    return dict_loc 


# Get the school information by scraping and crawling the web page from the cache file
# input: state (for those state names with more than 1 word, 
                # join them with "-" for the input. E.g., new-jersey)
# return: a list of school instances in the state
def get_schools(state_input):
    base_url = "https://www.internationalstudent.com"
    url = base_url + "/school-search/usa/" + state_input 
    url += "/?School%5BsearchProgram%5D=175" + "&School%5BsearchDegree%5D=4" 
    #limit all searches to Sociology with filter id 175
    # also limit all searches to doctorate degree with filter id 4
    
    page = get_schools_using_cache(url)
    soup = BeautifulSoup(page, "html.parser")
    
    # get the total number of web pages in this state
    try:
        num_page = int(soup.find(class_="summary").string[-1])
    except:
        num_page = 0
    
    school_list =[]
    if num_page > 0:
        for page in range(num_page):
            page_index = page+1
            url_update = base_url + "/school-search/usa/" + state_input + "/?School%5BsearchProgram%5D=175" 
            url_update += "&School%5BsearchDegree%5D=4" + "&School_page=" + str(page_index)
            page_update = get_schools_using_cache(url_update)
            soup_update = BeautifulSoup(page_update, "html.parser")
            
            schools = soup_update.find_all(class_="col text-secondary") # 25 schools on each page
            
            for i in schools:
                try:
                    # get the school name
                    school_name = i.find(class_="font-bitter text-left text-danger mb-2 mb-lg-0").string 
                    
                    # get the city and state name
                    school_city_state = i.find(class_="text-dark text-right").string
                    city = school_city_state.split(",")[0].strip()
                    state = school_city_state.split(",")[1].strip()

                    school_more = i.find(class_="col text-center order-sm-3")
                    school_url = school_more.find("a")["href"]
                    school_url_comp = base_url + school_url # url for a specific school

                    page_school = get_schools_using_cache(school_url_comp)
                    soup_school = BeautifulSoup(page_school, "html.parser")
                    
                    try:
                        student = soup_school.find(id="yw0")
                        stu_info = student.find_all(class_="f-12")
                        
                        # get the total number of students in the school
                        stu_total = stu_info[0].string 
                        
                        # get the total number of international students in the school
                        try:
                            stu_international = stu_info[3].string 
                        except:
                            stu_international = str(0)
                    except: # no information about students
                        pass
                    
                    # get the total number of faculty in the school
                    try:
                        faculty = soup_school.find(id="yw1")
                        fac_info = faculty.find_all(class_="f-12")
                        fac_total = fac_info[0].string 
                    except: # no information about faculty
                        pass 
                    
                    # get the total amount of tuition
                    try:
                        tuition = soup_school.find(class_="blue").string.strip()[15:]  
                    except: # no information about tuition
                        pass 
                    
                    # get the information about the address of the school
                    loc = soup_school.find(class_= "f-12 mt-2") 
                    
                    if loc.contents[2].strip() == "P:": 
                    # for those addresses that don't have street name
                        street = None
                    else:
                        try:
                            street = loc.contents[0].strip() # street name
                        except:
                            street = None

                    # get the type of the location including city, town, rural, suburb.
                    loc_info = soup_school.find(id="school-info-contact")
                    loc_info_more = loc_info.find(class_="mb-3")
                    locale = loc_info_more.contents[5].strip().split(":")[0] 
                    
                    # get the GPS coordinate of schools
                    try:
                        coor = get_coordinate(street, city, state) # coordinate
                        longitude = coor["longitude"]
                        latitude = coor["latitude"]
                    except:
                        coor = get_coordinate(school_name, city, state)
                        longitude = coor["longitude"]
                        latitude = coor["latitude"]
 
                    # create a school instance
                    school_ins = School(school_name, stu_total, stu_international, fac_total, tuition,
                                        street, city, state, locale, longitude, latitude) 

                    school_list.append(school_ins) # append the instance to the list of schools
                except: # for schools that don't have any information
                    pass
    else: # for states that don't have any schools of interest
        pass # actually no such a state exits
    return school_list


# Create an SQLite database called schoolinfo.db
def create_db():
    try: 
        conn = sqlite3.connect('schoolinfo.db')
        cur = conn.cursor()
    except Exception as e: # Print an error message if it fails.
        print(e)

    # clear out the database
    statement = '''
        DROP TABLE IF EXISTS 'Schools';
    '''
    cur.execute(statement)

    statement = '''
        DROP TABLE IF EXISTS 'States';
    '''
    cur.execute(statement)
    conn.commit()

    # Create two tables: Schools and States
    create_table_schools = '''
        CREATE TABLE "Schools" (
            'Id' INTEGER PRIMARY KEY AUTOINCREMENT,
            'Name' TEXT,
            'StudentTotal' INTEGER,
            'InternationalStudentTotal' INTEGER,
            'FacultyTotal' INTEGER,
            'Tuition' INTEGER,
            'Street' TEXT,
            'City' TEXT,
            'State' TEXT,
            'StateId' INTEGER,
            'Locale' TEXT,
            'Longitude' NUMERIC,
            'Latitude' NUMERIC
        );
    '''
    cur.execute(create_table_schools)
    conn.commit()

    create_table_states = '''
        CREATE TABLE "States" (
            'Id' INTEGER PRIMARY KEY AUTOINCREMENT,
            'State' TEXT,
            'StateCode' TEXT,
            'Region' TEXT,
            'Division' TEXT
        );
    '''
    cur.execute(create_table_states)
    conn.commit()
    conn.close()


# Populates using csv files of schools and states
def populate_db():

    # Connect to DB
    conn = sqlite3.connect('schoolinfo.db')
    cur = conn.cursor()

    # open the json file of countries
    with open('us census bureau regions and divisions.csv') as statesCSVFile: 
        d_states = csv.reader(statesCSVFile) 
        for row in d_states:
            # Insert the values to the table
            if row[0] != 'State': # Don't insert the first row
                insert_states = '''
                    INSERT INTO States
                    VALUES (?,?,?,?,?)
                '''
                values_states = (None, row[0], row[1], row[2], row[3])
                cur.execute(insert_states, values_states)
                conn.commit()

    with open('schools_output.csv') as schoolsCSVFile: 
        d_schools = csv.reader(schoolsCSVFile) 
        for row in d_schools:
            # Insert the values to the table
            if row[0] != 'Name': # Don't insert the first row
                insert_schools = '''
                    INSERT INTO Schools
                    SELECT ?,?,?,?,?,?,?,?,?,S.Id,?,?,?
                    FROM States AS S
                    WHERE S.State = ?
                '''
                values_schools = (None, row[0], row[1], row[2], row[3], row[4], row[5], 
                                  row[6], row[7], row[8], row[9],row[10],row[7])
                cur.execute(insert_schools, values_schools)
                conn.commit()     
    conn.close()


########## Invoke functions for data access and storage ###############
# Create a list of school instances from all US states

# Invoke the functions for data access
schools_list_all = []
with open('us census bureau regions and divisions.csv') as statesCSVFile: 
# open a csv file which contains all US states
# with this command, the file will be automatically closed after opening it
    d_states = csv.reader(statesCSVFile) 
    for row in d_states:
        if row[0] != "State":
            state_word = row[0].split()
            if len(state_word)>1: # join those state names with more than 1 word
                state = "-".join(state_word) 
                school_state = get_schools(state)
            else:
                school_state = get_schools(row[0]) # row[0] is the state name
            schools_list_all = schools_list_all + school_state # append the school instances in the state to the original

# write the data into a CSV
outfile = open("schools_output.csv","w")
outfile.write('"Name","StudentTotal","InternationalStudentTotal","FacultyTotal","Tuition","Street","City","State","Locale","longitude","latitude"\n') 
# note: don't put space after each comma
for i in schools_list_all:
    outfile.write('"{}","{}","{}","{}","{}","{}","{}","{}","{}","{}","{}"\n'.format(
                   i.name, int(i.student_total.replace(",","")), 
                   int(i.student_international.replace(",","")), int(i.faculty_total.replace(",","")), 
                   float(i.tuition.replace(",","")), i.street, i.city, 
                   i.state, i.locale.lower(), i.longitude, i.latitude))
outfile.close()

# Invoke the functions for creating database
create_db()
populate_db()


########## Functions: Data Processing and Presenting ##########

# Create a statement to draw school information from DB
# Input: a command from user
# return: a statement 
def sql_schools(command):
    words=command.split()

    # sql for selecting fields
    sql_fields = "SELECT S1.Name, S1.City, S1.State, S1.StudentTotal, S1.InternationalStudentTotal, S1.FacultyTotal, S1.Tuition, S1.Longitude, S1.Latitude"
    
    # sql for selecting tables
    sql_tables = "\nFROM Schools AS S1 JOIN States AS S2 ON S1.StateId = S2.Id"
    
    # sql for specifing condition
    if "region" not in command and "state" not in command and "locale" not in command:
        sql_where = ""
    else:
        if "state" in command:
            sql_where = "\nWHERE S2.StateCode = '" + words[1][6:] + "'"
        elif "locale" in command:
            sql_where = "\nWHERE S1.Locale = '" + words[1][7:] + "'"
        else:
            sql_where = "\nWHERE S2.Region = '" + words[1][7:] + "'"
    
    # sql for specifing ordering
    if "student" in command:
        sql_order = "\nORDER BY StudentTotal"
    elif "international" in command:
        sql_order = "\nORDER BY InternationalStudentTotal"
    elif "faculty" in command:
        sql_order = "\nORDER BY FacultyTotal"
    else:
        sql_order = "\nORDER BY Tuition"

    # sql for DESC
    if "bottom" in command:
        sql_desc = ""
    else:
        sql_desc = " DESC"

    # sql for specifing limit
    if "bottom" in command:
        sql_limit = "\nLIMIT " + str(words[-1][7:])
    elif "top" in command:
        sql_limit = "\nLIMIT " + str(words[-1][4:])
    else:
        sql_limit = "\nLIMIT 10" 

    sql_schools = sql_fields + sql_tables + sql_where + sql_order + sql_desc + sql_limit
    return sql_schools

# Create a statement to draw information of schools in specified states from DB 
# Input: a command from user
# return: a statement 
def sql_states(command):   
    words = command.split()
    # sql for selecting fields 
    sql_fields = "SELECT S1.State, S2.Region, SUM(StudentTotal),SUM(InternationalStudentTotal),SUM(FacultyTotal),ROUND(AVG(Tuition),2)"

    # sql for selecting tables   
    sql_tables = "\nFROM Schools AS S1 JOIN States AS S2 ON S1.StateId = S2.Id"

    # sql for specifing condition
    if "region" not in command and "locale" not in command:
        sql_where = ""
    else:
        if "region" in command:
            sql_where = "\nWHERE S2.Region = '" + words[1][7:] + "'"
        else:
            sql_where = "\nWHERE S1.Locale = '" + words[1][7:] + "'"
  
    # sql for grouping 
    sql_grouping ="\nGROUP BY S1.State"
    
    # sql for specifing ordering
    if "student" in command:
        sql_order = "\nORDER BY SUM(StudentTotal)"
    elif "international" in command:
        sql_order = "\nORDER BY SUM(InternationalStudentTotal)"
    elif "faculty" in command:
        sql_order = "\nORDER BY SUM(FacultyTotal)"
    else:
        sql_order = "\nORDER BY AVG(Tuition)"
    
    # sql for DESC
    if "bottom" in command:
        sql_desc = ""
    else:
        sql_desc = " DESC"

    # sql for specifing limit
    if "bottom" in command:
        sql_limit = "\nLIMIT " + str(words[-1][7:])
    elif "top" in command:
        sql_limit = "\nLIMIT " + str(words[-1][4:])
    else:
        sql_limit = "\nLIMIT 10" 

    sql_states = sql_fields + sql_tables + sql_where + sql_grouping + sql_order + sql_desc + sql_limit
    return sql_states

# Create a statement to draw information of schools in specified locales from DB 
# Input: a command from user
# return: a statement  
def sql_locales(command):
    words = command.split()
    # sql for selecting fields
    sql_fields = "SELECT S1.Locale, SUM(StudentTotal),SUM(InternationalStudentTotal),SUM(FacultyTotal),ROUND(AVG(Tuition),2)"
   
    # sql for selecting tables
    sql_tables = "\nFROM Schools AS S1 JOIN States AS S2 ON S1.StateId = S2.Id"
     
    # sql for specifing condition
    if "region" not in command and "state" not in command:
        sql_where = ""
    else:
        if "region" in command:
            sql_where = "\nWHERE S2.Region = '" + words[1][7:] + "'"
        else:
            sql_where = "\nWHERE S2.StateCode = '" + words[1][6:] + "'"

    # sql for grouping 
    sql_grouping ="\nGROUP BY S1.Locale"
    
    # sql for specifing ordering
    if "student" in command:
        sql_order = "\nORDER BY SUM(StudentTotal)"
    elif "international" in command:
        sql_order = "\nORDER BY SUM(InternationalStudentTotal)"
    elif "faculty" in command:
        sql_order = "\nORDER BY SUM(FacultyTotal)"
    else:
        sql_order = "\nORDER BY AVG(Tuition)"
    
    # sql for DESC
    if "bottom" in command:
        sql_desc = ""
    else:
        sql_desc = " DESC"

    # sql for specifing limit
    if "bottom" in command:
        sql_limit = "\nLIMIT " + str(words[-1][7:])
    elif "top" in command:
        sql_limit = "\nLIMIT " + str(words[-1][4:])
    else:
        sql_limit = "\nLIMIT 10" 

    sql_locales = sql_fields + sql_tables + sql_where + sql_grouping + sql_order + sql_desc + sql_limit
    return sql_locales

# Create a statement to draw information of schools in specified regions from DB 
# Input: a command from user
# return: a statement 
def sql_regions(command):
    words = command.split()
    # sql for selecting fields
    sql_fields = "SELECT S2.Region, SUM(StudentTotal),SUM(InternationalStudentTotal),SUM(FacultyTotal),ROUND(AVG(Tuition),2)"
   
    # sql for selecting tables
    sql_tables = "\nFROM Schools AS S1 JOIN States AS S2 ON S1.StateId = S2.Id"
     
    # sql for specifing condition
    if "locale" not in command:
        sql_where = ""
    else:
        sql_where = "\nWHERE S1.Locale = '" + words[1][7:] + "'"

    # sql for grouping 
    sql_grouping ="\nGROUP BY S2.Region"
    
    # sql for specifing ordering
    if "student" in command:
        sql_order = "\nORDER BY SUM(StudentTotal)"
    elif "international" in command:
        sql_order = "\nORDER BY SUM(InternationalStudentTotal)"
    elif "faculty" in command:
        sql_order = "\nORDER BY SUM(FacultyTotal)"
    else:
        sql_order = "\nORDER BY AVG(Tuition)"
    
    # sql for DESC
    if "bottom" in command:
        sql_desc = ""
    else:
        sql_desc = " DESC"

    # sql for specifing limit
    if "bottom" in command:
        sql_limit = "\nLIMIT " + str(words[-1][7:])
    elif "top" in command:
        sql_limit = "\nLIMIT " + str(words[-1][4:])
    else:
        sql_limit = "\nLIMIT 10" 

    sql_regions = sql_fields + sql_tables + sql_where + sql_grouping + sql_order + sql_desc + sql_limit
    return sql_regions

# Draw information from UB using the statement created above
# Input: a command from user
# Return: a list of tuples, each tuple contains information for one school
def process_command(command):
    try:
        conn = sqlite3.connect("schoolinfo.db")
        cur = conn.cursor()
    except Exception as e:
        print(e)

    if command.split()[0] == "schools":
        sql = sql_schools(command)
    elif command.split()[0] == "states":
        sql = sql_states(command)
    elif command.split()[0] == "locales":
        sql = sql_locales(command)
    else:
        sql = sql_regions(command)

    cur.execute(sql)
    info = cur.fetchall()
    conn.close()
    return info

# Center the plots in a map
# Input: two lists, one is with all latitude values, the other is with all longitude values
# Return four numbers that are going to use for ploting
def plot_to_center(lat_vals, lon_vals):
    ### Change the map scale to a certain state
    min_lat = 10000
    max_lat = -10000
    min_lon = 10000
    max_lon = -10000

    for str_v in lat_vals:
        v = float(str_v)
        if v < min_lat:
            min_lat = v
        if v > max_lat:
            max_lat = v
    for str_v in lon_vals:
        v = float(str_v)
        if v < min_lon:
            min_lon = v
        if v > max_lon:
            max_lon = v
    
    max_range = max(abs(max_lat - min_lat), abs(max_lon - min_lon))

    ### add pading to make the map less crowded
    padding = max_range * .1 # change this??
    lat_axis = [min_lat - padding, max_lat + padding]
    lon_axis = [min_lon - padding, max_lon + padding]

    ### Center the map
    center_lat = (max_lat+min_lat) / 2
    center_lon = (max_lon+min_lon) / 2

    return [lat_axis, lon_axis, center_lat, center_lon]


# Plot all of the schools
# param: a list of tuples, each tuple contains information for one school
# return: nothing
def plot_for_schools(schools_list):
    lat_vals = []
    lon_vals = []
    text_vals = []

    # create class instances for each tup in the list
    for tup in schools_list: 
        school_ins = Premap(tup)

        text_vals.append(school_ins.name)
        lat_vals.append(school_ins.latitude)
        lon_vals.append(school_ins.longitude)

    center = plot_to_center(lat_vals, lon_vals)

    data = [dict(
        type = 'scattergeo',
        locationmode = 'USA-states',
        lon = lon_vals,
        lat = lat_vals,
        text = text_vals,
        mode = 'markers',
        marker = dict(size = 12,symbol = 'star',color = 'red'))]

    layout = dict(
        title = ('Universities of Your Interest ' 
            + '<br>(Hover for more information of a particular school)'),
        geo = dict(
            scope='usa',
            projection=dict( type='albers usa' ),
            showland = True,
            #landcolor = "rgb(250, 250, 250)",
            landcolor = "grey",
            showlakes = True,
            lakecolor = ("light blue"),
            showsubunits = True,
            subunitcolor = "pink",
            showcountries = False,
            #countrycolor = "grey",
            lataxis = {'range': center[0]},
            lonaxis = {'range': center[1]},
            center= {'lat': center[2], 'lon': center[3]},
            countrywidth = 3,
            subunitwidth = 3))

    ### Run the data
    fig = dict(data=data, layout=layout)
    py.plot(fig, validate=False, filename='US Universities' )


# Plot a bar chart
# Param: 
  # a list of tuples, each tuple is a school
  # a keyword, which indicates the type of information that a user requests
# Return: None
def basic_barchart(slist, keyword):
    x = []
    y = []
    
    if keyword == "schools":
        for tup in slist:
            x.append(tup[0])
            y.append(tup[-3])     
        layout = dict(
        title='Tuition for Schools of Your Interest',xaxis=dict(
            tickfont=dict(
                size=9)))
    else:
        for tup in slist:
            x.append(tup[0])
            y.append(tup[-1])
        layout = dict(
        title='Average Tuition for States/Regions/Locales of Your Interest',
        xaxis=dict(
            tickfont=dict(
                size=9)))
    
    data = [go.Bar(
                x=x,
                y=y,
                text=y,
                textposition = 'auto',
                width = 0.5,
                marker=dict(
                    color='rgb(158,202,225)',
                    line=dict(color='rgb(8,48,107)',width=2)),
                opacity=0.6)]
    
    
    fig = dict(data=data, layout=layout)
    py.plot(fig, filename='Basic barchart') 


# Plot a bar chart
# Param: 
  # a list of tuples, each tuple is a school
  # a keyword, which indicates the type of information that a user requests
# Return: None
def group_barchart(slist,keyword):
    x = []
    y1 = []
    y2 = []
    y3 = []
    
    if keyword == "schools":
        for tup in slist:
            x.append(tup[0])
            y1.append(tup[3])
            y2.append(tup[4])
            y3.append(tup[5])
        layout = dict(
            title='No. of Students, International students, and Faculty at Schools of Your Interest',
            xaxis=dict(
                tickfont=dict(
                    size=9)))

    elif keyword == "states":
        for tup in slist:
            x.append(tup[0])
            y1.append(tup[2])
            y2.append(tup[3])
            y3.append(tup[4])
        layout = dict(
            title='Total No. of Students, International students, and Faculty in States of Your Interest',
            xaxis=dict(
                tickfont=dict(
                    size=9)))

    else:
        for tup in slist:
            x.append(tup[0])
            y1.append(tup[1])
            y2.append(tup[2])
            y3.append(tup[3])
        layout = dict(
            title='Total No. of Students, International students, and Faculty in Regions/Locales of Your Interest',
            xaxis=dict(
                tickfont=dict(
                    size=9)))

    trace1 = go.Bar(
        x=x,
        y=y1,
        text=y1,
        name="No. of students",
        textposition = 'auto',
        marker=dict(
            color='rgb(158,202,225)',
            line=dict(
                color='rgb(8,48,107)',
                width=1.5),
            ),
        opacity=0.6
    )

    trace2 = go.Bar(
        x=x,
        y=y2,
        text=y2,
        name="No. of international students",
        textposition = 'auto',
        marker=dict(
            color='rgb(58,200,225)',
            line=dict(
                color='rgb(8,48,107)',
                width=1.5),
            ),
        opacity=0.6
    )

    trace3 = go.Bar(
        x=x,
        y=y3,
        text=y3,
        name="No. of faculty",
        textposition = 'auto',
        marker=dict(
            color='rgb(128, 0, 128)',
            line=dict(
                color='rgb(8,48,107)',
                width=1.5),
            ),
        opacity=0.6
    )

    data = [trace1,trace2, trace3]
    fig = dict(data=data, layout=layout)
    py.plot(fig, filename='Grouped bar chart')


########## Data Presentation ##########
def load_help_text():
    with open('help.txt') as f:
        return f.read()

# Interactive
def interactive_prompt():
    help_text = load_help_text()
    response = ''
    
    while response != 'exit':
        response = input('Enter a command: ')

        if response == 'help':
            print(help_text) 
        elif response == "exit":
            print("Bye!")
            exit()
        else:
            words = response.split()

            try:
                if len(words) == 0:
                    print("bad command")
                else:
                    if words[0] == "schools" or words[0] =="states" or words[0] =="regions" or words[0] =="locales":
                        if (len(words) >=2 and "state=" not in words[1] and "region=" not in words[1] 
                            and "locale=" not in words[1] and "student" not in words[1] 
                            and "international" not in words[1] and "faculty" not in words[1] 
                            and "tuition" not in words[1] and "top=" not in words[1] and "bottom=" not in words[1]):
                            print("bad command")
                        elif (len(words) >=3 and "student" not in words[2] and "international" not in words[2] 
                            and "faculty" not in words[2] and "tuition" not in words[2] and "top=" not in words[2] 
                            and "bottom=" not in words[2]):
                            print("bad command")
                        elif len(words) >=4 and "top=" not in words[3] and "bottom=" not in words[3]:
                            print("bad command")
                        else:
                            keyword=words[0]
                            school_info = process_command(response)
                            if len(school_info) == 0:
                                print("We didn't find what you want.")
                            else:
                                for tup in school_info:
                                    str_=""
                                    if words[0] =="schools":
                                        if len(tup[0])>40:
                                            str_+='{0: <44}'.format(str(tup[0][:40])+"...")
                                        else:
                                            str_+='{0: <44}'.format(str(tup[0]))

                                        for i in tup[1:3]:
                                            if len(str(i))>20:
                                                str_+='{0: <22}'.format(str(i[:20])+"...")
                                            else:
                                                str_+='{0: <22}'.format(str(i))
                                    elif words[0] =="states":
                                        for i in tup[0:2]:
                                            if len(str(i))>20:
                                                str_+='{0: <25}'.format(str(i[:20])+"...")
                                            else:
                                                str_+='{0: <25}'.format(str(i))
                                    else:
                                        str_+=tup[0]

                                    print(str_)
                    
                    elif words[0]=="map":
                        try:
                            if keyword == "schools":
                                plot_for_schools(school_info) # probabality can create a class here
                            else:
                                print("There is not a result set of schools yet.")
                        except:
                            print("There is not a result set of schools yet.")


                    elif words[0]=="chart":
                        try:
                            if len(words)==1:
                                print("bad command")
                            else:
                                if words[1] == "tuition":
                                    basic_barchart(school_info, keyword)
                                elif words[1] == "demo":
                                    group_barchart(school_info, keyword)
                                else:
                                    print("bad command")
                        except:
                          print("There is not a result set of schools yet.")

                    else:
                        print("bad command")

            except:
               print("bad command")
           

# Only run when this file is a current file rather than a module
if __name__=="__main__":
    interactive_prompt()


