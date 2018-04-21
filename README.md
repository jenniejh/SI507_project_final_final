########## Data Source ##########
1. A website which can get information about all universities in the U.S.
   - Base URL: "https://www.internationalstudent.com"
   - Parameters for scraping and crawling
     1) state name
     2) program = 175 and degree = 4
        Restrict to schools that grant doctorate degree in sociology (to simplfy the project)
     3) page
   - Example for constructing the URL:
     1) First search by state and limit schools with doctorate degree in sociology in the U.S.
        We can get how many web pages we get for a specific state. e.g.:
        base_url + "/school-search/usa/" + "new-york" + "/?School%5BsearchProgram%5D=175" + "&School%5BsearchDegree%5D=4"
     2) Then scrape information on each page by specifying the number of page. e.g.:
        base_url + "/school-search/usa/" + "new-york" + "/?School%5BsearchProgram%5D=175" + "&School%5BsearchDegree%5D=4" + "&School_page=2"
     3) Find the url for each school and access data about that school with the url.

2. Google Place API's text search, to find GPS coordinate for schools
   - API instruction: https://developers.google.com/places/webservice/search
   - An API key is needed. Each key is only allowed for 100 calls per day.
     The API key is saved in a file named "secret_api.py". 
     The object name of the API key is "google_places_key".
   - A search query is needed. 
     I used "street name + city + state" or "school name + city + state" as the query.


########## Other information about running the program ##########
1. The name of the file for the main program: proj_final.py
2. The name of the file for testing the program: proj_final_test.py

3. About caching
   - Two caching files were created: 
     one is for the university web source; the other is for the Google API
   - The caching file for the university web source is too large to be uploaded to Github.
     You have to access data from the website (rather than the cache file) by running the code, 
     which will take a long time (10 minutes or so).
   - The caching file for the Google API is uploaded and I strongly recommend to use it because 
     of the limitation of 100 calls per day with Google API.

4. Comment out line 345-380 (approximate line numbers) if you want to grab data from database and 
   don't want to take time to run the code for accessing data from cache files for web sites.

5. About data processing and presenting
   - For most functions the only parameter that they need is a command from users.
     See the file help.txt for specification of the command.
   - There are three types of graphs: plotly map, plotly bar chart, ploty group bar chart.
     For each plot function we need a list of tuples grabbed from the database as a parameter.
     For the bar charts we also need a keyword grabbed from the user command as a parameter,
     which indicates how to organize the data that are grabbed from the database.
   - By calling the function interactive_prompt(), all functions can be called automatically 
     following your command.


########## Description of the struction of the code ##########
1. Step 1: Scape and crawl data from the website about U.S universities.
           Get data of universities of interest in all U.S. states.
           Related function: get_schools(state_input)
2. Step 2: Get the GPS coordinate for each school from Google API
           Related function: get_coordinate(street, city, state)
3. Step 3: Create an school instance for each school using Class School() to store the information
           that we grabbed online.
           Put all the instances in a list "schools_list_all" and then put them in a CSV file 
           (schools_output.csv).
4. Step 4: Read the CSV file as well as another CSV file about U.S. states 
           ("us census bureau regions and divisions.csv") into a database named "schoolinfo.db".
5. Step 5: Grab data from the database with four kinds of queries which are created by functions:
           - sql_schools(command): lists of schools, according to specified parameters.
           - sql_states(command): lists of states, according to specified parameters.
           - sql_locales(command): lists of locales, according to specified parameters.
           - sql_regions(command): lists of regions, according to specified parameters.
6. Step 6: Use Plotly to produce graphs with the data grabbed from the database.
           - A Class Premap() is used here to create the list of school instances for mapping.
7. Step 7: Create a interactive prompt for users to choose data/visualization options.


########## User guide ##########

See specification in the file "help.txt".


