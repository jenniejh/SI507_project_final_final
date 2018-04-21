import unittest
from proj_final import *


### Test data access from the data source about US universities and GPS coordinate
class TestSchoolAccess(unittest.TestCase):

    def school_is_in_list(self, school_name, school_list):
        for i in school_list:
            if school_name == i.name:
                return True
        return False

    def get_school_from_list(self, school_name, school_list):
        for i in school_list:
            if school_name == i.name:
                return i
        return None

    def get_gps(self, street, city, state):
        query = street + ", " + city + ", " + state
        base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params_d = {}
        params_d["query"] = query 
        params_d["key"] = secret_api.google_places_key
        resp = requests.get(base_url, params_d).text
        obj = json.loads(resp)
        return obj

    def setUp(self):
        self.mi_school_list = get_schools('michigan')
        self.ny_school_list = get_schools('new-york')
        self.msu = self.get_school_from_list('Michigan State University', self.mi_school_list)
        self.nyu = self.get_school_from_list('New York University', self.ny_school_list)

      
    def test_scaping(self):
        self.assertEqual(len(self.mi_school_list), 15)
        self.assertEqual(len(self.ny_school_list), 37)
        
        self.assertTrue(self.school_is_in_list('Michigan State University',self.mi_school_list))
        self.assertFalse(self.school_is_in_list('Michigan State University', self.ny_school_list))

    def test_school_demo(self):
        self.assertEqual(self.msu.student_total, '52,567')
        self.assertEqual(self.msu.student_international, '5,811')
        self.assertEqual(self.msu.faculty_total, '7,731')
        self.assertEqual(self.msu.tuition, '42,148.00')
        self.assertEqual(self.msu.street, '101 Marshall Adams Hall')
        self.assertEqual(self.msu.state, 'Michigan')
        self.assertEqual(self.msu.city, 'East Lansing')

    def test_school_gps(self):
        school1 = self.get_gps("101 Marshall Adams Hall", 'East Lansing', 'Michigan')
        school2 = self.get_gps("70 Washington Sq South", 'New York', 'New York')

        self.assertEqual(self.msu.longitude, school1["results"][0]["geometry"]["location"]["lng"])
        self.assertEqual(self.msu.latitude, school1["results"][0]["geometry"]["location"]["lat"])
        self.assertEqual(self.nyu.longitude, school2["results"][0]["geometry"]["location"]["lng"])
        self.assertEqual(self.nyu.latitude, school2["results"][0]["geometry"]["location"]["lat"])


### Test database is correctly constructured
class TestDatabase(unittest.TestCase):
    
    def test_schools_table(self):
        conn = sqlite3.connect('schoolinfo.db')
        cur = conn.cursor()

        sql = 'SELECT Name FROM Schools'
        results = cur.execute(sql)
        result_list = results.fetchall()
        self.assertIn(('Virginia State University',), result_list)
        self.assertEqual(len(result_list), 519)

        sql = '''
            SELECT Name,City,State,StudentTotal,InternationalStudentTotal,
                   FacultyTotal,Tuition,Longitude,Latitude
            FROM Schools
            WHERE State="Michigan"
            ORDER BY Tuition DESC
        '''
        results = cur.execute(sql)
        result_list = results.fetchall()
        self.assertEqual(len(result_list), 15)
        self.assertEqual(result_list[0][6], 50352)
        conn.close()

    def test_states_table(self):
        conn = sqlite3.connect('schoolinfo.db')
        cur = conn.cursor()

        sql = '''
            SELECT State
            FROM States
            WHERE Region="West"
        '''
        results = cur.execute(sql)
        result_list = results.fetchall()
        self.assertIn(('Utah',), result_list)
        self.assertEqual(len(result_list), 13)

        sql = '''
            SELECT COUNT(*)
            FROM States
        '''
        results = cur.execute(sql)
        count = results.fetchone()[0]
        self.assertEqual(count, 51)
        conn.close()

    # Test joins
    def test_joins(self):
        conn = sqlite3.connect('schoolinfo.db')
        cur = conn.cursor()

        sql = '''
            SELECT Region
            FROM States
                JOIN Schools
                ON Schools.StateId=States.Id
            WHERE Name="Princeton University"
        '''
        results = cur.execute(sql)
        result_list = results.fetchall()
        self.assertIn(('Northeast',), result_list)
        conn.close()


### Test grouping of data according to queries can produce the correct results
class TestQueries(unittest.TestCase):

    def test_school_search(self):
        results = process_command('schools students top=1')
        self.assertEqual(results[0][0], 'Liberty University')

        results = process_command('schools faculty bottom=10')
        self.assertEqual(results[0][0], 'Holy Apostles College and Seminary')

        results = process_command('schools locale=town top=5')
        self.assertEqual(results[3][3], 3456)

        results = process_command('schools region=South')
        self.assertEqual(results[9][6], 55992)

    def test_state_search(self):
        results = process_command('states region=West international top=5')
        self.assertEqual(results[3][0], 'Utah')

        results = process_command('states bottom=5')
        self.assertTrue(results[1][0] == 'Wyoming' and results[4][-1] == 27677.2)

    def test_locale_search(self):
        results = process_command('locales top=5')
        self.assertEqual(results[1][0],'city')

        results = process_command('locales region=Midwest students bottom=5')
        self.assertEqual(results[0][1], 99665)
        self.assertEqual(results[1][2], 12346)

    def test_region_search(self):
        results = process_command('regions international')
        self.assertEqual(results[0][0], 'South')
        self.assertEqual(results[3][2], 85629)
        self.assertEqual(len(results), 4)

        results = process_command('regions locale=rural bottom=3')
        self.assertEqual(len(results), 3)
        self.assertEqual(results[1][0], 'Midwest')
        self.assertGreater(results[2][4], 42790)


## Test graphs according to queries can work
class TestGraphs(unittest.TestCase):

    # we can't test to see if the maps are correct, but we can test that
    # the functions don't return an error!
    def test_show_map(self):
        slist = process_command("schools faculty bottom=10")
        try:
            plot_for_schools(slist)
        except:
            self.fail()

    def test_show_basic_barchart(self):
        query1 = "schools student bottom=10"
        query2 = "regions"
        slist1 = process_command(query1)
        slist2 = process_command(query2) 
        try:
            basic_barchart(slist1, query1.split()[0])
            basic_barchart(slist2, query2.split()[0])
        except:
            self.fail()
 
    def test_show_group_barchart(self):
        query1 = "schools student bottom=10"
        query2 = "states international top=5"
        query3 = "locales faculty"
        slist1 = process_command(query1)
        slist2 = process_command(query2)
        slist3 = process_command(query3)
        try:
            group_barchart(slist1, query1.split()[0])
            group_barchart(slist2, query2.split()[0])
            group_barchart(slist3, query3.split()[0])
        except:
            self.fail()
 

unittest.main(verbosity=2)


