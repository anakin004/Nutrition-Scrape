import sqlite3
import urllib.request, urllib.error
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
ua = UserAgent()
import collections 
collections.Callable = collections.abc.Callable



#looking at the nutrition charts, using bs4 to look at tables, get table data
base_url = 'https://www.nutrition-charts.com/'
restaurant_name = input('Enter a restaurant: ')
replaced_restaurant_name = restaurant_name.replace(' ','-')
url = f"{base_url}{replaced_restaurant_name}-nutrition-facts/"

# Add a User-Agent header to your request
header = {'User-Agent':str(ua.chrome)}
req = urllib.request.Request(url, headers=header)


try:
    con = urllib.request.urlopen(req)
    data = con.read().decode()
    soup = BeautifulSoup(data, 'html.parser')


    #finding all tables
    tables = soup.find_all("table")

    if tables:
        master_data = []

        # Extract table rows and columns
        for table in tables:
            table_data = []
            for row in table.find_all('tr'):
                row_data = [cell.text.strip() for cell in row.find_all(['th', 'td'])]
                table_data.append(row_data)
            master_data.append(table_data)

    else:
        print("No table found on the page.")

except urllib.error.HTTPError as e:
    print('HTTP Error')
    exit()
        


#this next part takes apart the data and puts it into a sql database


#parsing data
def foodpairs(table_data,table_headers,counter,foodlist):

    iteration = 0
    for food in range(1,len(table_data)):
        for attributes, data in zip(table_headers,table_data[food]):
        
            foodlist.append([attributes,data])
            
            if table_headers.index(attributes) == len(table_headers)-1 and iteration == counter:
                return foodlist
            if table_headers.index(attributes) == len(table_headers)-1:
                iteration += 1
                foodlist = []
                
def extract_words(input_list):
    for i in range(len(input_list)):
        word = input_list[i].split('(')[0]
        input_list[i] = word.replace(' ', '')




table_headers = table_data[0]
foodlist = []
counter = 0 

food_column = 'Food'
rest_columns = table_headers[1:]
extract_words(rest_columns)


#after getting table data we enter data into mysql to form a database
if data:

    dbhandle = restaurant_name + '.sqlite'
    conn = sqlite3.connect(dbhandle)
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS Nutrition')


#make a sql string based on the headers we have

columns_string = f'`{food_column}` TEXT, ' + ', '.join([f'`{header}` INTEGER' for header in rest_columns])
cur.execute(f'CREATE TABLE Nutrition ({columns_string})')

for p in master_data:
    while True:
    
        mainlist = foodpairs(p,table_headers,counter,foodlist)
        if not mainlist:
            break
        counter+=1
        food = mainlist[0][1]
    
    
        data = []
        for i in range(len(mainlist) - 1):
            temp = mainlist[i][1].replace(',', '').replace('.', '').replace('<','')
            next_item = mainlist[i + 1][1].replace(',', '').replace('.', '').replace('<','')
            try:
                int(next_item)
                data.append(temp)
            except ValueError:
                continue

    # Handle the last element separately
        try:
            int(mainlist[-1][1].replace(',', '').replace('.', '').replace('<',''))
            data.append(mainlist[-1][1])
        except:
            pass
    
        try:
            placeholders = ', '.join(['?' for _ in range(len(data))]) 
            insert_query = f'INSERT INTO Nutrition ({food_column}, {", ".join(rest_columns)}) VALUES ({placeholders})'
            cur.execute(insert_query, tuple(data))  # Convert data to a tuple using tuple(data)
            conn.commit()
        except:
            pass



import difflib

#find similar string function
def find_similar_strings(input_string, string_list, max_matches=5, threshold=0.6):
    # Check if the input string exactly matches any string in the list
    if input_string in string_list:
        return input_string

    # Use difflib to find the most similar strings
    matches = difflib.get_close_matches(input_string, string_list, n=max_matches, cutoff=threshold)
    return matches


allfoods = 'SELECT Food FROM Nutrition'
food_column_list = []
for food_tuple in cur.execute(allfoods):
    food = food_tuple[0]  # Extract the food name from the tuple
    if len(food) < 1:
        continue
    food_column_list.append(food)

#finding data about certain food
retrieve_info = input('Retrieve Food Info?Y/N')
if retrieve_info == 'Y':
    healthy_or_not = input('Enter a food from a restaurant: ')
    similar_string = find_similar_strings(healthy_or_not, food_column_list)
    food_find = None
    if type(similar_string) is list or not similar_string or similar_string in healthy_or_not:
        print('Search not valid, here are similar results, enter one',similar_string)
        food_find = input('Enter')
    if not food_find:
        food_find = similar_string

    select_food = f"SELECT * FROM Nutrition WHERE Food = ?"


    for row in cur.execute(select_food,(food_find,)):
        print('Data Fetched\n')
#create a final tuple that shows the food paired with the header, calories number paired with the word calories, etc.
    tuple_headers = tuple(table_headers)
    final_tuple = ()
    for header, data in zip(tuple_headers,row):
        final_tuple += (header,data)
#print('Data Returned, Returning Nutrition Data and Risks\n',final_tuple,'\n')

    health_risks = ''
    for i in range(2, len(final_tuple), 2):
        try:
            value = float(final_tuple[i+1])
        except ValueError:
            continue
    
        nutrient = final_tuple[i].rstrip().replace(' ', '').lower()
    
        if 'calories' in nutrient and value > 2000/3:
            health_risks += 'Excessive Calories, '
        elif 'totalfat' in nutrient and value > 58/3:
            health_risks += 'Too Much Fat, '
        elif 'trans' in nutrient and value > 0:
            health_risks += 'Trans Fat In Food, Any Amount Of Trans Fat Is Bad, '
        elif 'saturatedfat' in nutrient and value > 22/3:
            health_risks += 'Too Much Saturated Fat, '
        elif 'cholesterol' in nutrient and value > 250/3:
            health_risks += 'Too Much Cholesterol, '
        elif 'sodium' in nutrient and value > 2300/3:
            health_risks += 'Excessive Sodium, '
        elif 'carb' in nutrient and value > 280/3:
            health_risks += 'Too Much Carbohydrates, '
        elif 'fiber' in nutrient and value > 27/3:
            health_risks += 'Excessive Fiber, '
        elif 'sugar' in nutrient and value > 24/3:
            health_risks += 'Excessive Sugar, '
        elif 'protein' in nutrient and value > 90/3:
            health_risks += 'A lot of Protein, However protein is based on weight'

if retrieve_info == 'Y':

    yes_or_no = input('Do You Want To Know All Nutrition Data and Health Risks? Y/N')
    if yes_or_no == 'Y':
        print('In general, most adults should target their diets to comprise of 45-65% Carbohydrates, 10-35% Protein and 20-35% Fat.')
        print('Health Risks\n', health_risks)


#macro search, then count 
def macro_search():

    while True:
        macro = input('What Do You Want To Track - (Type Calories/Fat/Sodium/Etc)')
        similar_macro = find_similar_strings(macro, rest_columns)
        if len(similar_macro[0]) == 1:
            return similar_macro
        return similar_macro



def macro_count(tuple):
    temp = 0
    temp += tuple[0]
    return temp



#search macro
def calorie_tracker(food_column_list):
    macro_num = 0
    macro = macro_search()
    food_list = []
    while True:

        healthy_or_not = input('Enter a food from a restaurant: ')
        similar_string = find_similar_strings(healthy_or_not, food_column_list)
        
        if not healthy_or_not in similar_string:
            print('Search not valid, here are similar results, enter one',similar_string)
            similar_string = input('Enter')

        food_list.append(similar_string)

        search_query = f"SELECT {macro} FROM Nutrition WHERE Food = ?"
        cur.execute(search_query, (similar_string,))
        result = cur.fetchone()  # Fetch the first row

        #count cal
        retrieved_macro_count = macro_count(result)
    
        macro_num += retrieved_macro_count

        stop = input('Enter Another Food?Y/N   Or New Macro Enter M')
        if stop == 'N':
            print(macro,':',macro_num)
            return food_list
        elif stop == 'M':
            print(macro,':',macro_num)
            macro = macro_search()
            macro_num = 0
            continue
            
        print(macro,':',macro_num)
    

final = calorie_tracker(food_column_list)


print(final)
