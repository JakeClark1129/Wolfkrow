

import mysql.connector
import json

from wolfkrow.core import utils

__cursor = None

def get_wolfkrow_cursor(settings):
    if __cursor is None:
        __cursor = mysql.connector.connect(
            host=settings["wolfkrow"]["host"],
            user=settings["wolfkrow"]["user"],
            password=settings["wolfkrow"]["password"],
            database="wolfkrow_tasks"
        )

    return __cursor

def register_task(task, settings):
    cursor = get_wolfkrow_cursor(settings)
    
    sql = "INSERT INTO Tasks (name, inputs, outputs) VALUES (%s, %s, %s)"
    
    values = (task.name, json.dumps(task.inputs), json.dumps(task.outputs))
    
    cursor.execute(sql, values)
    
    cursor.commit()
    id = cursor.lastrowid
    task.id = id
    
    return id
