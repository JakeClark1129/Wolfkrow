

import mysql.connector
import json

from wolfkrow.core import utils

__cursor = None

class WolfkrowTaskDatabase:
    def __init__(self, connection):
        self.__connection = connection
        self.__cursor = self.__connection.cursor()
        
        self._initialize_db()

    def register_task(self, task):

        sql = "INSERT INTO tasks (name, inputs, outputs) VALUES (%s, %s, %s)"
        
        values = (
            task.name, 
            json.dumps(list(task.io_attributes["inputs"].keys())), 
            json.dumps(list(task.io_attributes["outputs"].keys()))
        )
        
        self.__cursor.execute(sql, values)
        
        self.__connection.commit()
        id = self.__cursor.lastrowid

        return id
    
    def register_output(self, task, output_attribute_name):
        
        sql = "INSERT INTO outputs (task_id, attribute_name) VALUES (%s, %s)"
        
        values = (task.id, output_attribute_name)
        
        self.__cursor.execute(sql, values)
        
        self.__connection.commit()
        id = self.__cursor.lastrowid

        return id

    def register_input(self, task_id, input_attribute_name, output_attribute_id):

        sql = """INSERT INTO inputs (task_id, attribute_name, output_attribute_id) 
                 VALUES (%s, %s, %s)"""

        values = (task_id, input_attribute_name, output_attribute_id)

        self.__cursor.execute(sql, values)

        self.__connection.commit()
        id = self.__cursor.lastrowid

        return id

    def register_output_data(self, task_id, attribute_name, output_data):
        
        sql = "UPDATE outputs SET output_data = %s WHERE task_id = %s AND attribute_name = %s"
        
        values = (output_data, task_id, attribute_name)
        
        self.__cursor.execute(sql, values)
        
        self.__connection.commit()

    def retrieve_input_data(self, task_id, attribute_name):
        
        sql = "SELECT output_attribute_id FROM inputs WHERE task_id = %s AND attribute_name = %s"
        
        values = (task_id, attribute_name)
        
        self.__cursor.execute(sql, values)
        output_id = self.__cursor.fetchone()[0]
        
        sql = "SELECT output_data FROM outputs WHERE id = %s"
        
        values = (output_id,)
        
        self.__cursor.execute(sql, values)
        output_data = self.__cursor.fetchone()[0]
        
        return output_data

    def _initialize_db(self):        
        self.__cursor.execute("CREATE DATABASE IF NOT EXISTS wolfkrow_tasks")
        self.__cursor.execute("USE wolfkrow_tasks")

        # Create a tasks table 
        self.__cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                name VARCHAR(255) NOT NULL, 
                status VARCHAR(50)
            )
            """
        )
        
        # Create a table for the inputs and outputs of each Task.
        # NOTE: Input's only store a reference to their related parent tasks output
        self.__cursor.execute("""CREATE TABLE IF NOT EXISTS inputs (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                task_id INT,
                attribute_name VARCHAR(255),
                output_attribute_id INT
            )
            """
        )
        
        self.__cursor.execute("""CREATE TABLE IF NOT EXISTS outputs (
                id INT AUTO_INCREMENT PRIMARY KEY, 
                task_id INT, 
                attribute_name VARCHAR(255),
                output_data TEXT
            )
            """
        )
        self.__connection.commit()
        

    @classmethod
    def _get_wolfkrow_cursor(cls, settings):
        cursor = mysql.connector.connect(
            host=settings.settings["wolfkrow"]["host"],
            user=settings.settings["wolfkrow"]["user"],
            password=settings.settings["wolfkrow"]["password"],
            database="wolfkrow_tasks"
        )

        return cursor

    @classmethod
    def from_settings(cls, settings):
        cursor = cls._get_wolfkrow_cursor(settings)
        return cls(cursor)
