import sqlite3 as sql
import os
import csv
from sqlite3 import Error

try:

  # Connect to database
  conn=sql.connect('database.db')


 # To view table data in table format
  print("******User Table Data*******")
  cur = conn.cursor()
  cur.execute('''SELECT * FROM User''')
  rows = cur.fetchall()
   
  for row in rows:
      print(row)

 # Export data into CSV file
  print("Exporting data into CSV............")
  cursor = conn.cursor()
  cursor.execute("select * from User")
  with open("user_data.csv", "w") as csv_file:
      csv_writer = csv.writer(csv_file, delimiter="\t")
      csv_writer.writerow([i[0] for i in cursor.description])
      csv_writer.writerows(cursor)

  dirpath = os.getcwd() + "/user_data.csv"
  print("Data exported Successfully into {}".format(dirpath))

except Error as e:
  print(e)

# Close database connection
finally:
  conn.close()
